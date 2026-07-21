# somfy-rpitx

라즈베리파이 GPIO 4와 `librpitx`를 이용해 한국형 Somfy Situo 5 RTS 계열을
447.7000 MHz FM-FSK로 제어하기 위한 실험용 프로그램입니다.

이 프로젝트는 기존 433.42 MHz OOK 구현의 RTS 데이터 계층을 그대로 사용합니다.
56비트 프레임, 명령 코드, 체크섬, 누적 XOR 난독화, 24비트 송신기 주소, 16비트
롤링 코드, Manchester 데이터, 최초/반복 프레임 타이밍은 RF 출력부와 분리되어
있습니다. RF 출력부만 두 개의 설정 가능한 FSK 톤과 반송파 OFF 상태로
바꿉니다.

Somfy 공식 한국형 Situo 1/5 RTS 자료는 447.7000 MHz, FM-FSK, RTS를 명시하고,
같은 JOO 447 MHz 계열의 공식 Telis 자료는 FSK 편이를 `±3 kHz`로 명시합니다.
따라서 설치 예제의 초기 프로파일은 447.697/447.703 MHz입니다. 다만 현재
Situo 5 모델 자료에는 편이와 논리 극성이 직접 적혀 있지 않으므로, `±3 kHz`는
동일 제조사·동일 지역·동일 RTS RF 계열에서 도출한 높은 신뢰도의 초기값이지
해당 리모컨을 계측한 결과는 아닙니다.

> **중요:** 두 톤 중 어느 쪽이 논리 high인지는 공개 자료에서 확인되지
> 않았습니다. 먼저 `dry-run`과 SDR로 검증하고, 필요하면
> `invert_mark_space`만 바꾸십시오. 주파수와 편이는 하드코딩되어 있지 않습니다.

## 안전 및 법적 주의

`rpitx`는 인증된 송신기가 아니며 GPIO에서 기본파 외 고조파와 불요파가 강하게
나올 수 있습니다. 안테나를 바로 연결하지 말고 적절한 447.7 MHz 대역통과 필터,
감쇠기, 차폐, 더미 로드를 사용해 SDR/스펙트럼 분석기로 먼저 검증하십시오.
실제 송신 전에 대한민국의 현재 주파수 이용 조건, 허용 출력, 점유대역폭,
불요발사, 적합성평가 요건을 직접 확인해야 합니다. 프로젝트와 rpitx 모두 전파
규정 적합성을 보증하지 않습니다.

기본 설정은 다음 세 안전장치를 둡니다.

- 코드 자체의 편이 기본값은 없으며, 설치 예제에만 조사값 `±3 kHz`가 있습니다.
- `transmit_enabled` 기본값은 `false`입니다.
- 실제 송신은 root 권한과 설치된 네이티브 백엔드가 있어야 합니다.

## 구조

| 모듈 | 역할 |
|---|---|
| `protocol.py` | RTS 명령, 56비트 프레임, 체크섬, 난독화 |
| `pulses.py` | Situo 5 타이밍, Manchester 펄스, 반복 프레임 |
| `modulation.py` | 논리 펄스를 설정 가능한 mark/space FSK 톤으로 매핑 |
| `storage.py` | 가상 리모컨 주소와 롤링 코드를 잠금·원자 저장 |
| `transmitter.py` | 검증 후 네이티브 librpitx 백엔드 실행 |
| `dryrun.py` | 프레임, 비트, 전체 펄스, 주파수 표 출력 |
| `cli.py` | `up`, `down`, `stop`, `prog`, `dry-run` CLI |
| `native/somfy_rpitx_tx.cpp` | `librpitx::fskburst` DMA 송신과 RF 공백 처리 |
| `homebridge/` | HomeKit WindowCovering 동적 플랫폼과 위치 추정 |
| `config.schema.json` | Homebridge UI 설정 스키마 |

## RTS 구현 기준

- 명령: `MY/STOP=0x1`, `UP=0x2`, `DOWN=0x4`, `PROG=0x8`
- 프레임: 7바이트/56비트, MSB first
- 주소: 24비트, 프레임 내 little-endian
- 롤링 코드: 16비트 big-endian, 명령 한 번당 1 증가
- 암호화 키: `0xA0 | (rolling_code & 0x0f)`
- 체크섬: clear frame 모든 nibble의 XOR
- 난독화: `frame[i] ^= frame[i-1]` 누적 XOR
- Manchester: `1 = low→high`, `0 = high→low`
- 일반 명령: 최초 프레임 1개 + 반복 2개
- PROG: 최초 프레임 1개 + 반복 3개

기본 타이밍은 Open RTS가 실제 Situo 5에서 측정한 프로파일입니다.

| 구간 | 기본값 |
|---|---:|
| wakeup high / low | 10568 / 7072 µs |
| hardware sync high / low | 2585 / 2436 µs |
| software sync high / low | 4898 / 644 µs |
| Manchester half-symbol | 644 µs |
| inter-frame gap | 26838 µs |

최초 프레임의 hardware sync는 2쌍, 반복 프레임은 7쌍입니다. 반복 프레임은
최초 프레임과 같은 주소, 롤링 코드, 난독화된 페이로드를 사용합니다.
Manchester와 sync의 low 구간은 SPACE 톤으로 송신하지만, wakeup separator와
inter-frame gap은 GPIO 4의 RF clock을 끕니다. Somfy의 RTS 특허도 반복 프레임
사이를 “no signal” 구간으로 설명합니다.

## 설치

Raspberry Pi OS에서 먼저 공식 rpitx/librpitx를 설치합니다.

```sh
git clone https://github.com/F5OEO/rpitx.git
cd rpitx
./install.sh
sudo reboot
```

재부팅 후 이 프로젝트를 설치합니다.

```sh
git clone https://github.com/AppStudioLB/somfy-rpitx.git
cd somfy-rpitx
make test
make native
sudo make install
```

`make native`는 `/usr/local`에 설치된 `librpitx`와 링크합니다. 배포판의 Python
패키지 정책 때문에 `sudo make install`의 `pip` 단계가 거부되면 가상환경에
Python 패키지를 설치하고 CLI를 `/usr/local/bin`에 연결해도 됩니다.

```sh
python3 -m venv .venv
.venv/bin/pip install .
sudo ln -s "$PWD/.venv/bin/somfy-rpitx" /usr/local/bin/somfy-rpitx
sudo install -m 0755 build/somfy-rpitx-tx /usr/local/bin/somfy-rpitx-tx
sudo install -d -m 0750 /etc/somfy-rpitx /var/lib/somfy-rpitx
sudo install -m 0640 config.example.json /etc/somfy-rpitx/config.json
```

## 한국/JOO 447 MHz FSK 프로파일

조사 결과와 적용 범위는 다음과 같습니다.

| 항목 | 적용값 | 근거 |
|---|---:|---|
| 중심 주파수 | 447,700,000 Hz | 현행 Situo 1/5 RTS Korea 공식 자료 |
| 변조 | FM-FSK | 현행 Situo 1/5 RTS Korea 공식 자료 |
| 편이 | ±3,000 Hz | 공식 Telis JOO 447 MHz RTS 계열 자료 |
| 낮은/높은 톤 | 447,697,000 / 447,703,000 Hz | 중심 ± 편이 |
| 논리 high 극성 | 현장 확인 필요 | 공개 자료에 미기재 |
| 방사전력 | 0 dBm/1 mW | 현행 Situo 1/5 RTS Korea 공식 자료 |

`config.example.json`은 이 프로파일을 사용하지만 실제 송신은 꺼져 있습니다.
설치 후 `/etc/somfy-rpitx/config.json`의 기본 RF 부분은 다음과 같습니다.

```json
{
  "rf": {
    "center_frequency_hz": 447700000,
    "deviation_hz": 3000,
    "mark_frequency_hz": null,
    "space_frequency_hz": null,
    "invert_mark_space": false,
    "tick_us": 4
  },
  "transmit_enabled": false
}
```

이 방식은 `mark=center+deviation`, `space=center-deviation`으로 계산합니다.
즉 기본값은 MARK 447.703 MHz, SPACE 447.697 MHz입니다. 여기서 MARK/SPACE는
프로그램 내부 이름이며, `invert_mark_space=true`는 두 실제 주파수를 바꾸지
않고 논리 high/low의 배정만 뒤집습니다.

SDR로 두 톤을 직접 측정했다면 아래처럼 편이 대신 주파수를 지정할 수 있습니다.

```json
{
  "rf": {
    "center_frequency_hz": 447700000,
    "deviation_hz": null,
    "mark_frequency_hz": "<MEASURED_MARK_HZ>",
    "space_frequency_hz": "<MEASURED_SPACE_HZ>",
    "invert_mark_space": false,
    "tick_us": 4
  },
  "transmit_enabled": false
}
```

두 직접 주파수는 반드시 서로 다른 실제 측정값으로 바꾸십시오. 직접
`mark_frequency_hz`와 `space_frequency_hz`를 모두 설정하면 이 값들이
`deviation_hz`보다 우선합니다. 두 톤은 항상 쌍으로 설정해야 합니다.

`tick_us=4`에서는 각 펄스가 가장 가까운 4 µs로 양자화됩니다. 기본 Situo 5
펄스의 오차는 펄스당 최대 2 µs입니다.

### 실기 확인 순서

1. 안테나 대신 감쇠기·더미 로드·근접 결합 SDR 환경을 구성합니다.
2. `sudo somfy-rpitx dry-run prog`에서 447697000/447703000 Hz와 OFF 구간을
   확인합니다.
3. 실제 리모컨을 SDR로 캡처할 수 있으면 편이가 약 ±3 kHz인지, 첫 wakeup 뒤와
   프레임 사이에 반송파가 꺼지는지 비교합니다.
4. 리모컨의 Manchester 상승 에지가 어느 톤 전이인지 확인해
   `invert_mark_space`를 결정합니다.
5. 캡처가 없다면 `false`로 한 번만 등록을 시도하고, 응답이 없을 때 rolling
   code가 증가한 것을 확인한 뒤 `true`로 바꿔 다시 시도합니다.

FSK 극성은 주소·rolling code·등록 상태와 무관하므로 설정을 뒤집어도 가상
리모컨 주소를 새로 만들 필요는 없습니다. 다만 PROG 반복은 모터에 따라 등록
해제로 해석될 수 있으므로 해당 모터 설명서의 등록 대기 절차 안에서만
시험하십시오.

## dry-run

사용자 설정에서 편이값을 제거해도 프레임과 펄스는 출력되며 주파수는
`UNSET`으로 표시됩니다. 설치 예제는 조사값 `±3 kHz`를 사용합니다. dry-run은
롤링 코드를 소비하지 않습니다. 상태 파일이 처음 사용되는 경우에만 새 24비트
가상 리모컨 주소를 생성해 영구 저장합니다.

```sh
sudo somfy-rpitx dry-run prog
sudo somfy-rpitx dry-run up
```

출력에는 다음이 포함됩니다.

- clear/난독화 프레임과 56개 on-air 비트
- 가상 리모컨 주소와 사용할 롤링 코드
- center/deviation/mark/space/invert 설정
- 모든 wakeup, sync, data, gap 펄스의 시작 시각과 길이
- 각 펄스에 대응하는 MARK/SPACE/OFF 및 실제 주파수

다른 설정이나 상태 파일로 시험하려면:

```sh
somfy-rpitx --config ./config.json \
  --state-file ./state.json dry-run prog
```

## 새 가상 리모컨 등록

이 프로그램은 기존 Situo 리모컨의 주소나 롤링 코드를 복제하지 않습니다.
첫 dry-run 또는 첫 실제 명령 때 무작위 24비트 주소를 하나 생성하고, 이를
별도의 새 리모컨으로 모터에 등록합니다.

1. 먼저 `sudo somfy-rpitx dry-run prog` 출력과 두 FSK 톤을 SDR로 검증합니다.
2. 출력 필터와 전력이 적절한지 확인합니다.
3. 설정의 `transmit_enabled`를 `true`로 바꿉니다.
4. 이미 등록된 실제 리모컨의 PROG 버튼을 모터가 짧게 움직일 때까지 누릅니다.
5. 모터의 등록 대기 시간 안에 `sudo somfy-rpitx prog`를 한 번 실행합니다.
6. 모터가 다시 짧게 움직이면 `up/down/stop`으로 확인합니다.

모터별 정확한 등록/해제 절차와 PROG 누름 시간은 해당 Somfy 모터 설명서를
우선하십시오. `prog`를 불필요하게 반복하면 등록 해제로 해석될 수 있습니다.

## 사용

```sh
sudo somfy-rpitx up
sudo somfy-rpitx down
sudo somfy-rpitx stop
sudo somfy-rpitx prog
sudo somfy-rpitx dry-run prog
```

실제 송신은 설정과 백엔드 검증을 먼저 끝낸 다음 롤링 코드를 상태 파일에서
원자적으로 예약합니다. 송신 도중 장애가 나면 해당 코드는 재사용하지 않고
건너뜁니다. 이는 코드 중복 사용으로 수신기와 동기화가 깨지는 것보다 안전한
방향입니다.

## Homebridge 전동 블라인드 등록

같은 Raspberry Pi에서 Homebridge를 실행하면 이 저장소를
`homebridge-somfy-rpitx` 동적 플랫폼 플러그인으로 설치할 수 있습니다. Apple
홈에는 표준 `WindowCovering` 서비스로 나타나며 다음 동작을 지원합니다.

- 0%=완전히 닫힘, 100%=완전히 열림
- 목표 위치가 증가하면 `up`, 감소하면 `down`
- 1~99% 중간 위치에 도달하면 자동 `stop`
- HomeKit의 Hold/정지 요청을 `stop`으로 전달
- 여러 블라인드와 각기 다른 가상 리모컨 상태 파일 지원
- `prog`는 실수로 등록을 해제하지 않도록 HomeKit에 노출하지 않음

RTS에는 위치 피드백이 없으므로 현재 위치는 설정한 전체 개폐 시간으로
추정합니다. 실제 리모컨이나 벽 스위치로 움직이면 HomeKit 위치와 어긋날 수
있습니다. 이때 HomeKit에서 완전 열기 또는 완전 닫기를 실행해 끝단 위치를 다시
맞추십시오. Homebridge가 중간 위치 이동 중 비정상 종료되면 예약된 STOP이
실행되지 않을 수 있으므로 모터의 물리적 끝단과 장애물 감지 기능을 전제로
사용해야 합니다. 정상 종료 신호에서는 플러그인이 먼저 STOP을 시도합니다.

### 1. 플러그인 설치

먼저 앞 절의 Python CLI와 네이티브 송신기를 설치하고, 실제
`sudo somfy-rpitx up/down/stop`이 작동하는지 확인합니다. Homebridge 공식
Debian/Raspberry Pi 서비스 설치의 플러그인 경로를 사용하려면:

```sh
sudo hb-service add 'git+https://github.com/AppStudioLB/somfy-rpitx.git'
```

일반 npm 전역 방식으로 Homebridge를 설치했다면:

```sh
sudo npm install -g --omit=dev \
  'git+https://github.com/AppStudioLB/somfy-rpitx.git'
```

이 플러그인은 Homebridge 1.8/2.x를 지원하며 별도 npm 런타임 의존성이
없습니다. Homebridge 1.x에서는 Node.js 20을 사용할 수 있고, Homebridge
2.x는 공식 요구사항에 따라 Node.js 22 또는 24가 필요합니다. Homebridge와
GPIO 4 송신기는 같은 Raspberry Pi에 있어야 합니다. 일반적인 격리 Docker
컨테이너에서는 호스트의 GPIO·DMA·sudo에 접근할 수 없으므로 그대로는
동작하지 않습니다.

### 2. Homebridge 전용 sudo 권한

Homebridge 서비스는 보통 `homebridge` 사용자로 실행되지만 rpitx 송신은
root가 필요합니다. 전체 CLI에 포괄적인 sudo 권한을 주지 말고, 사용할 설정과
상태 파일 및 세 명령만 정확히 허용합니다.

`sudo visudo -f /etc/sudoers.d/homebridge-somfy-rpitx`로 다음 내용을
추가합니다. 줄바꿈의 `\`도 그대로 사용하십시오.

```sudoers
Cmnd_Alias SOMFY_RPITX = \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-1.json up, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-1.json down, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-1.json stop, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-2.json up, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-2.json down, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-2.json stop, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-3.json up, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-3.json down, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/blind-3.json stop, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/all-blinds.json up, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/all-blinds.json down, \
  /usr/local/bin/somfy-rpitx --config /etc/somfy-rpitx/config.json --state-file /var/lib/somfy-rpitx/all-blinds.json stop

homebridge ALL=(root) NOPASSWD: SOMFY_RPITX
```

문법과 비밀번호 없는 실행을 확인합니다.

```sh
sudo visudo -cf /etc/sudoers.d/homebridge-somfy-rpitx
sudo -l -U homebridge
```

출력에는 위 12개 명령만 나타나야 합니다. 실제 실행 권한은 커튼이 움직여도
안전한 상태에서 `sudo -u homebridge sudo -n ... up` 전체 명령을 한 번
실행해 확인하십시오. UI에서 고유 ID나 별도 설정·상태 파일 경로를 변경했다면
sudoers의 해당 경로도 똑같이 변경해야 합니다.

### 3. Homebridge 설정

Homebridge UI에서 **Plugins → Homebridge Somfy rpitx → Settings**를 엽니다.
처음 설정 화면에는 다음 네 항목이 자동으로 준비됩니다.

- 블라인드 1, 블라인드 2, 블라인드 3: 각 모터를 독립 제어
- 전체 블라인드: 세 모터를 동시에 제어하는 그룹

각 항목에서 표시 이름, 고유 ID, 완전히 열리고 닫히는 시간만 확인하면 됩니다.
공통 RF 설정 파일은 `/etc/somfy-rpitx/config.json`, 가상 리모컨 저장 폴더는
`/var/lib/somfy-rpitx`가 기본값입니다. 별도 상태 파일을 입력하지 않으면
고유 ID를 이용해 다음처럼 자동 생성합니다.

```text
/var/lib/somfy-rpitx/blind-1.json
/var/lib/somfy-rpitx/blind-2.json
/var/lib/somfy-rpitx/blind-3.json
/var/lib/somfy-rpitx/all-blinds.json
```

UI에서 **제어 종류**를 `개별 블라인드` 또는 `전체/그룹 블라인드`로 선택할 수
있습니다. 이 값은 설정 화면에서 용도를 명확히 구분하기 위한 것으로 RTS
프레임을 변경하지는 않습니다. 그룹 항목의 가상 리모컨 주소를 제어할 모든
모터에 등록하면 해당 HomeKit 타일 하나로 모두 움직입니다.

고급 설정의 별도 RF 설정 파일과 별도 상태 파일은 기존 설정을 이전하거나
특정 항목만 다른 RF 프로파일을 사용할 때만 입력합니다. 서로 다른 항목에
같은 상태 파일을 지정하면 플러그인이 시작을 거부하여 롤링 코드 충돌을
방지합니다.

UI 대신 `/var/lib/homebridge/config.json`을 직접 편집하려면 `platforms`
배열에 다음처럼 추가할 수 있습니다. UI 기본 설정과 같은 구성입니다.

```json
{
  "platform": "SomfyRpitx",
  "name": "Somfy rpitx",
  "cliPath": "/usr/local/bin/somfy-rpitx",
  "useSudo": true,
  "sudoPath": "/usr/bin/sudo",
  "commandTimeoutSeconds": 15,
  "configPath": "/etc/somfy-rpitx/config.json",
  "stateDirectory": "/var/lib/somfy-rpitx",
  "blinds": [
    {
      "id": "blind-1",
      "name": "블라인드 1",
      "remoteType": "individual",
      "openTimeSeconds": 25,
      "closeTimeSeconds": 25,
      "initialPosition": 0
    },
    {
      "id": "blind-2",
      "name": "블라인드 2",
      "remoteType": "individual",
      "openTimeSeconds": 25,
      "closeTimeSeconds": 25,
      "initialPosition": 0
    },
    {
      "id": "blind-3",
      "name": "블라인드 3",
      "remoteType": "individual",
      "openTimeSeconds": 25,
      "closeTimeSeconds": 25,
      "initialPosition": 0
    },
    {
      "id": "all-blinds",
      "name": "전체 블라인드",
      "remoteType": "group",
      "openTimeSeconds": 25,
      "closeTimeSeconds": 25,
      "initialPosition": 0
    }
  ]
}
```

`id`는 HomeKit 액세서리 UUID의 기준이므로 등록 후 바꾸지 마십시오.
`openTimeSeconds`와 `closeTimeSeconds`는 각각 완전 닫힘→열림,
완전 열림→닫힘을 스톱워치로 측정한 값입니다.

### 4. 개별 리모컨과 전체 그룹 등록

설정을 저장하면 먼저 각 상태 파일을 만들고 주소를 확인합니다. `dry-run`은
롤링 코드를 소비하지 않습니다.

```sh
sudo somfy-rpitx --state-file /var/lib/somfy-rpitx/blind-1.json dry-run prog
sudo somfy-rpitx --state-file /var/lib/somfy-rpitx/blind-2.json dry-run prog
sudo somfy-rpitx --state-file /var/lib/somfy-rpitx/blind-3.json dry-run prog
sudo somfy-rpitx --state-file /var/lib/somfy-rpitx/all-blinds.json dry-run prog
```

그다음 각 개별 주소를 해당 모터 하나에만 PROG 등록합니다. 마지막으로
`all-blinds.json` 주소를 1·2·3번 모터에 각각 PROG 등록합니다. 그룹 등록도
한 번에 세 모터로 방송하는 과정이 아니라, 같은 가상 리모컨을 각 모터가
차례로 학습하도록 하는 과정입니다. 정확한 등록 대기 진입 방법과 PROG 누름
시간은 모터 설명서를 따르십시오.

설정 후 Homebridge를 재시작합니다.

```sh
sudo hb-service restart
sudo hb-service logs
```

로그에 `Adding blind` 또는 `Restoring blind`가 나타나면 Apple 홈에서
Homebridge 브리지를 통해 전동 블라인드가 표시됩니다.

## 상태 파일의 내구성

기본 상태 파일은 `/var/lib/somfy-rpitx/state.json`입니다.

```json
{
  "next_rolling_code": 2,
  "remote_address": 1193046,
  "version": 1
}
```

- `state.json.lock`에 POSIX `flock(LOCK_EX)` 적용
- 같은 디렉터리에 mode `0600` 임시 파일 생성
- JSON 기록 후 파일 `fsync`
- `os.replace`로 원자 교체
- 상위 디렉터리 `fsync`
- 알 수 없는 필드, 손상된 JSON, 범위 밖 값은 덮어쓰지 않고 오류 처리

이 파일을 잃으면 이미 등록한 가상 리모컨의 롤링 코드도 잃습니다. 정기적으로
보호된 위치에 백업하십시오. 복원할 때 오래된 롤링 코드로 되돌리지 마십시오.
카운터가 소진 보호값에 도달하면 새 주소로 다시 등록해야 합니다.

## 테스트

```sh
make test
npm test
npm run test:syntax
```

테스트는 공개 Open RTS 기준 벡터, 체크섬/난독화, 주소 byte order, 명령 코드,
Situo 5 펄스 수와 반복 동기, FSK 유도/직접 설정/극성 반전, dry-run 출력,
상태 파일 권한과 증가, 실제 송신 안전장치 및 subprocess 입력을 검증합니다.
Node 테스트는 Homebridge 설정 검증, 명령 주입 방지, sudo/CLI 인자, 개폐별
위치 추정과 정지를 검증합니다.

네이티브 코드만 헤더 수준에서 확인하려면 Raspberry Pi에서:

```sh
c++ -std=c++14 -Wall -Wextra -fsyntax-only native/somfy_rpitx_tx.cpp
```

실제 RF 검증은 반드시 더미 로드 또는 충분한 감쇠와 필터를 거친 계측 환경에서
별도로 수행해야 합니다.

## 참고 자료

- [PushStack: Somfy RTS Protocol](https://pushstack.wordpress.com/somfy-rts-protocol/)
- [Open RTS](https://github.com/loopj/open-rts)
- [Somfy: Situo 1 & 5 RTS for Korea 공식 자료](https://service.somfy.com/downloads/master_v4_b2c/datasheet-_situo_1_-_5_rts_korea.pdf)
- [Somfy: Telis 4 RTS Pure 447 MHz for JOO 공식 자료](https://service.somfy.com/downloads/kr_v5/181072703-01_telis-4-rts-pure-447mhz_control.pdf)
- [Somfy RTS 프레임·inter-frame silence 특허](https://patents.google.com/patent/US8189620B2/en)
- [rpitx](https://github.com/F5OEO/rpitx)
- [librpitx](https://github.com/F5OEO/librpitx)
- [Homebridge Plugin API](https://developers.homebridge.io/homebridge/)
- [Homebridge Debian/Raspberry Pi 서비스 설치](https://github.com/homebridge/homebridge/wiki/Install-Homebridge-on-Debian-or-Ubuntu-Linux)
- [국가법령정보센터: 신고하지 아니하고 개설할 수 있는 무선국용 무선설비의 기술기준](https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulId=53943&efYd=0)

## 라이선스

Python 프로젝트와 이 저장소의 네이티브 연결 소스는 MIT 라이선스입니다.
`librpitx`는 GPL-3.0이며 MIT는 GPL과 호환되지만, `librpitx`와 링크된 최종
실행 파일을 배포할 때는 GPL-3.0 조건이 적용됩니다.
