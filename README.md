[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mmBvcuTa)
# Hackathon Problem - Quantum Radar Battleship

## Team Information
- **Team Name**: Sheldon
- **QFF-Registered Email IDs**:
  - `lakshya.jindal@research.iiit.ac.in`

---

## Overview

This project implements a quantum solution to the game of **Battleship** based on the **Elitzur-Vaidman (E-V) Interaction-Free Measurement** principle (from `Battleship.docx` and `Battleship-PPT.pdf`, Qiskit Fall Fest 2025).

In traditional Battleship, finding a hidden ship requires firing a direct shot, causing an explosion if a ship is hit. Here, we implement a **Quantum Radar** that scans the grid using quantum superposition and interference to detect and locate all enemy ships with minimal chance of hitting them, securing victory before firing a single destructive shot.

### Core Capabilities
1. **Full Elitzur-Vaidman Quantum Circuit (Slide 9, 10, 16)**: Implements the exact multi-qubit Mach-Zehnder interferometer circuit with physical measurement gates on ship qubits (`q_target`) and the probe qubit (`q_probe`), executed on Qiskit's `AerSimulator`.
2. **Real Physical Quantum Simulation**: Every shot physically evaluates whether the ship cell collapsed the wavefunction ("BOOM!" explosion) or whether the dark port detector fired without explosion ("Bomb Found" interaction-free detection).
3. **Full-Fleet Battleship Simulation**: Simulates authentic naval gameplay with multi-cell ships (Battleship, Cruiser, Submarine, Destroyer, Patrol Boat) placed horizontally and vertically without overlapping.
4. **Quantum Disambiguation Engine**: Solves multi-ship candidate ambiguity ("ghost" intersections) using targeted single-cell quantum EV probes, achieving 100% precision with 0 false positives.
5. **Direct Classical vs. Quantum Benchmark**: Quantifies quantum advantage against classical brute-force hunt (which requires up to $N^2$ scans and inflicts 100% damage on hits).
6. **Tracked Results & Visualizations**: Automatically exports complete experimental logs, ASCII circuit diagrams, structured JSON metrics, and 4-panel publication-grade plots to `results/`.

---

## Mathematical & Quantum Foundation

### 1. The Elitzur-Vaidman Thought Experiment (1993)
Avshalom Elitzur and Lev Vaidman demonstrated that quantum superposition and wavefunction collapse enable detecting the presence of an ultra-sensitive object (a "bomb" or ship) **without triggering it**.

In an optical Mach-Zehnder interferometer:
- A single photon is split by beam splitter 1 ($BS_1$, modeled by $R_x(\theta)$).
- Reference arm $|0\rangle$ and Bomb arm $|1\rangle$ are created in superposition:
  $$\vert\psi_1\rangle = \cos(\theta/2)\vert 0\rangle - i\sin(\theta/2)\vert 1\rangle$$
- **Case A: No Bomb / Ship Present**:
  The photon passes through both arms unperturbed, recombines at beam splitter 2 ($BS_2$, modeled by $R_x(-\theta)$), and experiences constructive interference at the bright port (Detector 0) and completely destructive interference at the dark port (Detector 1).
  $$P(\text{Detector 0}) = 100\%, \quad P(\text{Detector 1}) = 0\%, \quad P(\text{Explosion}) = 0\%$$
- **Case B: Bomb / Ship Present**:
  The ship acts as a measuring observer.
  - With probability $P(\text{boom}) = \sin^2(\theta/2)$, the photon is measured in the bomb arm $\to$ **BOOM! (Ship Explodes)**.
  - With probability $\cos^2(\theta/2)$, the photon is measured in the reference arm $\to$ state collapses to $|0\rangle$ without exploding.
  - The collapsed photon reaches $BS_2$ alone (no interference). At $BS_2$, it has probability $\sin^2(\theta/2)$ of being deflected into the dark port (Detector 1).
  - Therefore, the probability of **Interaction-Free Detection** without explosion is:
    $$P(\text{detection}) = \cos^2(\theta/2)\sin^2(\theta/2)$$

### 2. Theoretical E.V. Score
The Elitzur-Vaidman quality factor is defined as the ratio of interaction-free detections to explosions:
$$\text{E.V. Score} = \frac{P(\text{detection})}{P(\text{explosion})} = \frac{\cos^2(\theta/2)\sin^2(\theta/2)}{\sin^2(\theta/2)} = \cos^2(\theta/2)$$

- **Original Experiment ($\theta = \pi/2$, Slide 9)**:
  $$P(\text{boom}) = 50.0\%, \quad P(\text{detection}) = 25.0\%, \quad \text{E.V. Score} = \frac{25\%}{50\%} = 50.0\%$$
- **Angle Upgrade ($\theta = \pi/3$, Slide 10 & 16)**:
  $$P(\text{boom}) = \sin^2(\pi/6) = 25.0\%$$
  $$P(\text{detection}) = \cos^2(\pi/6)\sin^2(\pi/6) = (0.75)(0.25) = 18.75\%$$
  $$\text{E.V. Score} = \frac{18.75\%}{25.0\%} = 75.0\%$$

---

## Quantum Circuit Architecture (Slide 16 Spec)

For a Battleship line probe (column or row with $N$ cells), the circuit consists of:
- $1$ Probe Qubit ($q_0$)
- $N$ Cell Target Qubits ($q_1, \dots, q_N$)
- Classical bits for measuring each ship cell and the probe qubit.

```
     ┌─────────┐                    ┌────────┐ ░     ░ ┌───────┐               ┌──────────┐┌─┐
q_0: ┤ Rx(π/3) ├──■────■────■────■──┤ Rx(-π) ├─░─────░─┤ Rx(π) ├──■────■────■──■──┤ Rx(-π/3) ├┤M├
     └─────────┘┌─┴─┐  │    │    │  └────────┘ ░     ░ └───────┘┌─┴─┐  │    │  │  └──────────┘└╥┘
q_1: ───────────┤ X ├──┼────┼────┼─────────────░─────░──────────┤ X ├──┼────┼──┼───────────────╫─
                └───┘┌─┴─┐  │    │             ░ ┌─┐ ░          └───┘┌─┴─┐  │  │               ║ 
q_2: ────────────────┤ X ├──┼────┼─────────────░─┤M├─░───────────────┤ X ├──┼──┼───────────────╫─
                     └───┘┌─┴─┐  │             ░ └╥┘ ░               └───┘┌─┴─┐│               ║ 
q_3: ─────────────────────┤ X ├──┼─────────────░──╫──░────────────────────┤ X ├┼───────────────╫─
                          └───┘┌─┴─┐           ░  ║  ░                    └───┘│               ║ 
q_4: ──────────────────────────┤ X ├───────────░──╫──░─────────────────────────■───────────────╫─
                               └───┘           ░  ║  ░                                         ║ 
c: 2/═════════════════════════════════════════════╩════════════════════════════════════════════╩═
                                                  0                                            1 
```

### Steps:
1. **$R_x(\pi/3)$ on $q_0$**: Creates probe superposition.
2. **CNOTs from $q_0$ to $q_1 \dots q_N$**: Entangles the probe photon with all cells in the scanned line.
3. **$R_x(-\pi)$ on $q_0$**: Aligns probe phase for the interference check.
4. **Intermediate Measurement on Ship Cells**: Any ship present in the line acts as a bomb detector and measures its target qubit. If it measures $1$, the ship explodes ("BOOM!"). If $0$, the wavefunction collapses safely.
5. **$R_x(\pi)$ on $q_0$ + CNOTs + $R_x(-\pi/3)$**: Recombines the arms through the second beam splitter.
6. **Probe Measurement**: Measures $q_0$ into classical bit `c_probe`. If $c[0] == 0$ (no ship explosion) and $c[1] == 1$ (probe clicked), an **interaction-free detection** has occurred!

---

## Battleship Game Architecture & Search Strategy

```
                          +-------------------------------+
                          |   Battleship Board Setup      |
                          |  (e.g., 4x4 Destroyer C2-D2)  |
                          +---------------+---------------+
                                          |
                                          v
                          +-------------------------------+
                          | PHASE 1: Line Sweeps          |
                          | Quantum Superposition Scan    |
                          | - Probes all N columns        |
                          | - Probes all N rows           |
                          | (2N measurements vs N^2)      |
                          +---------------+---------------+
                                          |
                                          v
                          +-------------------------------+
                          | PHASE 2: Candidate Analysis   |
                          | Intersect Hot Rows & Hot Cols |
                          +---------------+---------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                 No Ambiguity                       Ambiguity Present
           (|Candidates| == |Fleet|)             (|Candidates| > |Fleet|)
                        |                                   |
                        v                                   v
             Confirmed Ship Locations             +-------------------+
                                                  | Targeted 1-Cell   |
                                                  | Quantum EV Probes |
                                                  +---------+---------+
                                                            |
                                                            v
                                                  Filtered Ship Locations
                                                            |
                                          +-----------------+
                                          v
                          +-------------------------------+
                          | PHASE 3: Game Completion      |
                          | - Verify 100% Detection       |
                          | - Compute Real EV Metrics     |
                          | - Compare against Classical   |
                          | - Export JSON, PNG, TXT       |
                          +-------------------------------+
```

---

## Setup & Running with Python Virtual Environment

### 1. Prerequisites
- Python 3.9, 3.10, or 3.11 installed on the system.

### 2. Create and Activate Virtual Environment
On **Windows (PowerShell)**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On **Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Quantum Battleship Simulation
Run the simulation (runs the challenging 8x8 full-fleet game by default):
```bash
python solution.py
```

Run with custom CLI parameters:
```bash
# Run the 4x4 presentation benchmark scenario (Slide 13/16 spec):
python solution.py --scenario benchmark

# Run the 4x4 multi-ship disambiguation scenario:
python solution.py --scenario multi

# Run with theta = pi/2 (50% theoretical EV score, Slide 9):
python solution.py --angle pi/2

# Adjust shots per quantum probe:
python solution.py --shots 10000
```

---

## Challenging Full-Fleet Simulation Results (8x8 Grid, 5 Ships)

To simulate a non-trivial, realistic game of Battleship, the default configuration executes on an **8x8 grid (64 cells)** with a complete 5-vessel naval fleet:
- **Battleship** (length 4): `B2, C2, D2, E2` (horizontal)
- **Cruiser** (length 3): `G4, G5, G6` (vertical)
- **Submarine** (length 3): `B7, C7, D7` (horizontal)
- **Destroyer** (length 2): `C4, C5` (vertical)
- **Patrol Boat** (length 2): `H1, H2` (vertical)
**Total Ship Segments**: 14 segments across 64 grid cells.

### Quantum Radar Scan & Disambiguation Log
```
[PHASE 1] Quantum Superposition Line Sweeps...
Scanning Columns...
  Col A: Clear (0 ships)
  Col B: DETECTED! (Rate: 18.8%, Explosions: 984)
  Col C: DETECTED! (Rate: 18.2%, Explosions: 1002)
  Col D: DETECTED! (Rate: 18.1%, Explosions: 967)
  Col E: DETECTED! (Rate: 19.1%, Explosions: 1015)
  Col F: Clear (0 ships)
  Col G: DETECTED! (Rate: 18.5%, Explosions: 1042)
  Col H: DETECTED! (Rate: 18.9%, Explosions: 999)

Scanning Rows...
  Row 1: DETECTED! (Rate: 18.9%, Explosions: 966)
  Row 2: DETECTED! (Rate: 18.4%, Explosions: 976)
  Row 3: Clear (0 ships)
  Row 4: DETECTED! (Rate: 18.8%, Explosions: 982)
  Row 5: DETECTED! (Rate: 17.8%, Explosions: 1051)
  Row 6: DETECTED! (Rate: 19.6%, Explosions: 971)
  Row 7: DETECTED! (Rate: 18.9%, Explosions: 992)
  Row 8: Clear (0 ships)

[PHASE 2] Candidate Analysis & Quantum Disambiguation:
  Hot Columns: ['B', 'C', 'D', 'E', 'G', 'H'] (6 hot columns)
  Hot Rows:    ['1', '2', '4', '5', '6', '7'] (6 hot rows)
  Raw Intersection Count: 36 candidate cells (for 14 actual ship parts)
  Running targeted Quantum EV probes on candidate cells...
    Cell H1: Confirmed SHIP via interaction-free probe! (Det: 18.9%)
    Cell B2, C2, D2, E2, H2: Confirmed SHIP via interaction-free probe!
    Cell C4, G4: Confirmed SHIP via interaction-free probe!
    Cell C5, G5: Confirmed SHIP via interaction-free probe!
    Cell G6: Confirmed SHIP via interaction-free probe!
    Cell B7, C7, D7: Confirmed SHIP via interaction-free probe!
    22 Empty Water Cells correctly filtered out with 0 detections!
```

### Final Classified Board
```
    A   B   C   D   E   F   G   H
  +---+---+---+---+---+---+---+---+
1 | ~ | ~ | ~ | ~ | ~ | ~ | ~ | O |
  +---+---+---+---+---+---+---+---+
2 | ~ | O | O | O | O | ~ | ~ | O |
  +---+---+---+---+---+---+---+---+
3 | ~ | ~ | ~ | ~ | ~ | ~ | ~ | ~ |
  +---+---+---+---+---+---+---+---+
4 | ~ | ~ | O | ~ | ~ | ~ | O | ~ |
  +---+---+---+---+---+---+---+---+
5 | ~ | ~ | O | ~ | ~ | ~ | O | ~ |
  +---+---+---+---+---+---+---+---+
6 | ~ | ~ | ~ | ~ | ~ | ~ | O | ~ |
  +---+---+---+---+---+---+---+---+
7 | ~ | O | O | O | ~ | ~ | ~ | ~ |
  +---+---+---+---+---+---+---+---+
8 | ~ | ~ | ~ | ~ | ~ | ~ | ~ | ~ |
  +---+---+---+---+---+---+---+---+
Legend: O = Found Ship, ~ = Water
```

### Performance & Scoring Metrics (8x8 Fleet)
| Metric | Quantum Radar | Classical Brute-Force | Advantage / Significance |
| :--- | :---: | :---: | :---: |
| **Grid Scans Needed** | **52** (16 lines + 36 targeted) | **64** | **18.8% fewer measurements** |
| **Ships Located** | **14 / 14 (100.0%)** | 14 / 14 (100.0%) | Full accuracy on complex 2D fleet |
| **False Positives** | **0** | 0 | All 22 ghost cells eliminated |
| **Simulated Physical Explosions** | **25,810** | Direct hit on every ship | Minimized quantum damage |
| **Interaction-Free Detections** | **19,392** | 0 | Proved interaction-free probing |
| **Empirical E.V. Score** | **75.13%** | 0.0% | Spot on theoretical $75.0\%$ |
| **Slide 17 Battleship Score** | **0.609** | 0.000 | $\frac{\text{Detection}}{\text{Explosion}} \times \frac{\text{Measurements}}{\text{Brute-force}}$ |
| **Speedup-Adjusted Score** | **0.923** | 0.000 | $\frac{\text{Detection}}{\text{Explosion}} \times \frac{\text{Brute-force}}{\text{Measurements}}$ |

---

## Benchmark Scenario (Slide 13/14/16 Presentation Board)

In addition to the 8x8 fleet, the 4x4 presentation board from `Battleship-PPT.pdf` is also validated:
- **Dimensions**: $4 \times 4$ ($16$ cells)
- **Fleet**: Destroyer (length 2) placed at coordinates **C2** and **D2**.
- **Quantum Measurements**: **8** (4 cols + 4 rows) vs **16** for classical (a **50.0% reduction**).
- **Ships Located**: 2 / 2 (100.0%), 0 false positives.
- **Empirical E.V. Score**: **74.15%** (theoretical: $75.00\%$).
- **Slide 17 Battleship Score**: **0.375**, Speedup-adjusted score: **1.500**.
- **Artifact**: Saved in [`results/benchmark_4x4_summary.json`](results/benchmark_4x4_summary.json).

---

## Multi-Ship Disambiguation Results

When multiple ships are on the board, line scans identify all hot rows and columns. Their Cartesian product creates ghost intersections:
- Ships placed: Destroyer at **C2-D2**, Patrol Boat at **A4-B4**.
- Hot Columns: `['A', 'B', 'C', 'D']`
- Hot Rows: `['2', '4']`
- Raw Candidates: 8 cells (`A2, B2, C2, D2, A4, B4, C4, D4`).
- **Targeted Quantum Probing**:
  - Cell A2: Empty $\to$ Confirmed WATER
  - Cell B2: Empty $\to$ Confirmed WATER
  - Cell C2: Ship $\to$ Confirmed SHIP via interaction-free probe (Det: 19.1%)
  - Cell D2: Ship $\to$ Confirmed SHIP via interaction-free probe (Det: 18.9%)
  - Cell A4: Ship $\to$ Confirmed SHIP via interaction-free probe (Det: 19.4%)
  - Cell B4: Ship $\to$ Confirmed SHIP via interaction-free probe (Det: 19.2%)
  - Cell C4: Empty $\to$ Confirmed WATER
  - Cell D4: Empty $\to$ Confirmed WATER
- **Result**: 100% precision and recall (4 out of 4 ships found, 0 false positives).

---

## Generated Results & Artifacts

All experimental results are generated and committed directly to the repository in `results/`:
- [`results/quantum_battleship_analysis.png`](results/quantum_battleship_analysis.png): 4-panel publication visualization showing:
  1. Battleship grid map (detected vs water)
  2. Quantum circuit shot outcome distribution (matching Slide 16 histogram)
  3. Quantum vs Classical performance comparison
  4. Theoretical EV score curve across rotation angles $\theta \in [0, \pi]$
- [`results/simulation_summary.json`](results/simulation_summary.json): Complete machine-readable JSON summary of the 8x8 game, shots, explosions, detections, and metrics.
- [`results/simulation_report.txt`](results/simulation_report.txt): Detailed ASCII simulation report for the 8x8 naval game.
- [`results/circuit_diagram.txt`](results/circuit_diagram.txt): ASCII quantum circuit diagram matching Slide 16.
- [`results/benchmark_4x4_summary.json`](results/benchmark_4x4_summary.json): 4x4 Slide 13/16 presentation benchmark results.
- [`results/multi_ship_summary.json`](results/multi_ship_summary.json): Multi-ship disambiguation benchmark summary.

---

## File Structure

```
├── Battleship.docx                   # Problem statement document
├── Battleship-PPT.pdf                # Presentation specification slides
├── solution.py                       # Full Quantum Radar Battleship Simulator
├── requirements.txt                  # Python library dependencies
├── README.md                         # Documentation and complete report
├── .gitignore                        # Git ignore (.venv, __pycache__)
└── results/                          # TRACKED results and figures
    ├── benchmark_4x4_summary.json    # 4x4 Presentation benchmark data
    ├── circuit_diagram.txt           # Quantum circuit ASCII diagram
    ├── multi_ship_summary.json       # Multi-ship disambiguation results
    ├── quantum_battleship_analysis.png # 4-panel visual performance plot
    ├── simulation_report.txt         # Formatted text simulation report (8x8)
    └── simulation_summary.json       # Structured benchmark JSON data (8x8)
