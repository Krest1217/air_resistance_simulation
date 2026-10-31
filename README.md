# 공기저항 실험실

Python 표준 라이브러리로 만든 2차원 공기저항 시뮬레이션입니다. **다운로드한 뒤 인터넷 없이 실행**할 수 있습니다. 외부 패키지, 서버, API 키가 필요하지 않습니다.

## 로컬 실행

1. Python 3.10 이상을 설치합니다. Windows/macOS는 python.org 배포판의 Tcl/Tk 포함 설치를 권장합니다.
2. 이 저장소를 ZIP으로 다운로드하고 압축을 풉니다.
3. 해당 폴더에서 실행합니다.

```sh
python main.py
```

macOS/Linux에서는 `python3 main.py`를 사용할 수 있습니다. Linux에서 tkinter가 없다면 배포판 패키지(예: Ubuntu의 `sudo apt install python3-tk`)를 먼저 설치하세요. 최초 Python/Tk 설치 이후에는 네트워크가 필요 없습니다. 그래픽 데스크톱이 필요하며, `no display name` 오류는 화면 없는 서버에서 실행했다는 뜻입니다.

## 사용 방법

- 형상: 구, 정육면체, 유선형체
- 입력: 초기 속력(m/s), 질량(kg), 크기(m), 발사각(수평 기준 °), 발사 높이(m)
- 크기: 구는 **지름**, 정육면체는 **한 변**, 유선형체는 **장축 전체 길이**입니다.
- 실행하면 공기저항이 있는 궤적과 없는 궤적, 비행시간·사거리·최고 높이를 비교합니다.
- 재생 버튼이나 시간 슬라이더로 운동에너지·위치에너지·공기저항으로 잃은 에너지를 확인합니다. 기본 화면은 착지 순간입니다.
- CSV 저장은 조건과 모든 계산 시점의 위치·속도·에너지를 내보냅니다. 입력을 바꾼 뒤 다시 실행하기 전까지 결과는 직전 실험을 나타냅니다.

## 물리 모델

### 공기 조건

$$
T = 298\,\mathrm{K}, \qquad p = 1\,\mathrm{atm}
$$

$$
\rho = \frac{101325}{287.05 \times 298} \approx 1.1845\,\mathrm{kg/m^3}
$$

$$
\mu = 1.837 \times 10^{-5}\,\mathrm{Pa\cdot s}, \qquad g = 9.80665\,\mathrm{m/s^2}
$$

### 항력과 레이놀즈 수

$$
F_d = \frac{1}{2}\rho A C_d v^2, \qquad \mathrm{Re} = \frac{\rho v L}{\mu}
$$

### 구 — 지름 d

$$
A = \pi\left(\frac{d}{2}\right)^2, \qquad L = d
$$

$$
C_d = \begin{cases}
\displaystyle \frac{24}{\mathrm{Re}}\left(1 + 0.15\,\mathrm{Re}^{0.687}\right), & 0 < \mathrm{Re} < 1000 \\
0.44, & \mathrm{Re} \geq 1000
\end{cases}
$$

### 정육면체 — 한 변의 길이 a

$$
A = a^2, \qquad L = a, \qquad C_d = \frac{24}{\mathrm{Re}} + 1.05
$$

### 유선형체 — 장축 전체 길이 ℓ

$$
\text{장축}:\text{단축} = 4:1, \qquad \text{단축 지름} = \frac{\ell}{4}
$$

$$
A = \pi\left(\frac{\ell}{8}\right)^2, \qquad L = \frac{\ell}{4}, \qquad C_d = \frac{24}{\mathrm{Re}} + 0.10
$$

### 역학적 에너지

$$
E_k = \frac{1}{2}mv^2, \qquad E_p = mgy, \qquad E = E_k + E_p
$$

$$
E_0 = \frac{1}{2}mv_0^2 + mgh_0, \qquad E_{\mathrm{loss}} = E_0 - E
$$

## 검증

```sh
python -m unittest discover -s tests -v
```

무저항 해석해, 에너지 보존·감소, 착지 이벤트, 세 형상, 시간 간격 수렴과 입력 검증을 검사합니다. `physics.py`는 GUI 없이도 사용할 수 있습니다.
