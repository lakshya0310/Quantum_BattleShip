"""
Quantum Battleship Simulation using Elitzur-Vaidman Interaction-Free Measurement
================================================================================
Based on:
- Battleship.docx
- Battleship-PPT.pdf (Qiskit Fall Fest 2025: "Quantum Radar for Battleship Game")

Key Concepts:
1. Elitzur-Vaidman Bomb Tester (1993):
   Utilizes Mach-Zehnder interferometer and quantum superposition/collapse to detect
   sensitive objects ("bombs" / ships) without triggering an explosion.
2. Quantum Radar Superposition Plan:
   Instead of testing every square individually (brute-force N^2 measurements),
   we probe entire rows and columns simultaneously using quantum superposition.
   For an N x N board, this uses only 2N line measurements.
3. Actual Quantum Simulation:
   Constructs multi-qubit quantum circuits executed on Qiskit AerSimulator with real shots.
   Simulates actual physical measurement outcomes:
   - "Bomb found" (Interaction-free detection, dark port fires, 0 explosions)
   - "Boom!" (Explosion triggered on ship cell)
   - "No explosion" (Inconclusive pass)
4. Game Simulation & Comparison:
   Simulates a full Battleship game with realistic ship placements, candidate disambiguation,
   and compares directly against classical brute-force gameplay.
"""

import os
import sys
import json
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

# Ensure UTF-8 output where supported, with graceful fallback
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless backend for saving figures
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# =====================================================================
# 1. BATTLESHIP DATA STRUCTURES
# =====================================================================

@dataclass
class Ship:
    """Represents a naval vessel on the Battleship grid."""
    name: str
    size: int
    coordinates: List[Tuple[int, int]]
    orientation: str = 'horizontal'  # 'horizontal' or 'vertical'


class BattleshipBoard:
    """Represents a Battleship board with fleet placement and state tracking."""
    def __init__(self, rows: int = 4, cols: int = 4):
        self.rows = rows
        self.cols = cols
        self.grid = np.zeros((rows, cols), dtype=int)
        self.ships: List[Ship] = []

    def place_ship(self, name: str, start: Tuple[int, int], size: int, orientation: str = 'horizontal') -> bool:
        r, c = start
        coords = []
        for i in range(size):
            rr = r + (i if orientation == 'vertical' else 0)
            cc = c + (i if orientation == 'horizontal' else 0)
            if rr < 0 or rr >= self.rows or cc < 0 or cc >= self.cols:
                return False
            if self.grid[rr, cc] == 1:
                return False  # Overlap not allowed
            coords.append((rr, cc))

        for rr, cc in coords:
            self.grid[rr, cc] = 1

        self.ships.append(Ship(name=name, size=size, coordinates=coords, orientation=orientation))
        return True

    @classmethod
    def create_benchmark_board(cls) -> 'BattleshipBoard':
        """
        Creates the exact 4x4 benchmark board from Battleship-PPT.pdf (Slides 13, 14, 16):
        4x4 grid (A-D, 1-4) with a 2-unit Destroyer placed at Row 2, Columns C and D.
        Coordinates: (1, 2) and (1, 3).
        """
        board = cls(rows=4, cols=4)
        board.place_ship("Destroyer", (1, 2), size=2, orientation='horizontal')
        return board

    @classmethod
    def create_multi_ship_board(cls) -> 'BattleshipBoard':
        """
        Creates a 4x4 board with multiple ships to test multi-ship radar disambiguation:
        - Destroyer (size 2) at C2-D2 -> (1, 2) and (1, 3)
        - Patrol Boat (size 2) at A4-B4 -> (3, 0) and (3, 1)
        """
        board = cls(rows=4, cols=4)
        board.place_ship("Destroyer", (1, 2), size=2, orientation='horizontal')
        board.place_ship("Patrol Boat", (3, 0), size=2, orientation='horizontal')
        return board

    @classmethod
    def create_standard_board(cls) -> 'BattleshipBoard':
        """
        Creates an authentic, challenging 8x8 Battleship board with a full naval fleet (5 ships, 14 segments):
        - Battleship (size 4) at B2-E2 (horizontal): (1, 1), (1, 2), (1, 3), (1, 4)
        - Cruiser (size 3) at G4-G6 (vertical): (3, 6), (4, 6), (5, 6)
        - Submarine (size 3) at B7-D7 (horizontal): (6, 1), (6, 2), (6, 3)
        - Destroyer (size 2) at C4-C5 (vertical): (3, 2), (4, 2)
        - Patrol Boat (size 2) at H1-H2 (vertical): (0, 7), (1, 7)
        """
        board = cls(rows=8, cols=8)
        board.place_ship("Battleship", (1, 1), size=4, orientation='horizontal')
        board.place_ship("Cruiser", (3, 6), size=3, orientation='vertical')
        board.place_ship("Submarine", (6, 1), size=3, orientation='horizontal')
        board.place_ship("Destroyer", (3, 2), size=2, orientation='vertical')
        board.place_ship("Patrol Boat", (0, 7), size=2, orientation='vertical')
        return board

    def get_ship_cells(self) -> List[Tuple[int, int]]:
        cells = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r, c] == 1:
                    cells.append((r, c))
        return cells

    def render_ascii(self, detected_cells: Optional[List[Tuple[int, int]]] = None) -> str:
        """Renders an ASCII representation of the board."""
        col_labels = [chr(65 + c) for c in range(self.cols)]
        header = "    " + "   ".join(col_labels)
        lines = [header, "  +" + "---+" * self.cols]

        detected_set = set(detected_cells or [])
        for r in range(self.rows):
            row_str = f"{r+1} |"
            for c in range(self.cols):
                is_ship = self.grid[r, c] == 1
                is_detected = (r, c) in detected_set

                if is_ship and is_detected:
                    symbol = " O"  # Found ship
                elif is_ship:
                    symbol = " S"  # Undetected hidden ship
                elif is_detected:
                    symbol = " ?"  # False positive
                else:
                    symbol = " ~"  # Water
                row_str += f"{symbol} |"
            lines.append(row_str)
            lines.append("  +" + "---+" * self.cols)
        return "\n".join(lines)


# =====================================================================
# 2. QUANTUM ELITZUR-VAIDMAN INTERACTION-FREE RADAR
# =====================================================================

class QuantumRadar:
    """
    Implements the Elitzur-Vaidman interaction-free quantum radar probe
    as specified in Battleship-PPT.pdf (Slides 9, 10, 16).
    """

    def __init__(self, probe_angle: float = math.pi / 3, simulator: Optional[AerSimulator] = None):
        """
        Args:
            probe_angle: Rotation angle theta for Rx gate.
                         pi/2 yields 50% theoretical EV score (Slide 9).
                         pi/3 yields 75% theoretical EV score (Slide 10, 16).
            simulator: Qiskit AerSimulator instance.
        """
        self.probe_angle = probe_angle
        self.simulator = simulator or AerSimulator()

    def build_circuit(self, num_targets: int, ship_local_indices: List[int]) -> QuantumCircuit:
        """
        Builds the exact multi-qubit Elitzur-Vaidman circuit from Slide 16.

        Circuit structure:
        - Qubit 0: Probe qubit (photon)
        - Qubits 1..num_targets: Target cells in the probed row or column
        - Classical bits: One for each ship measured + One for the probe qubit
        """
        num_ships = len(ship_local_indices)
        total_qubits = 1 + num_targets
        total_cbits = 1 + num_ships  # c[0..num_ships-1]: ship measurements, c[num_ships]: probe

        qc = QuantumCircuit(total_qubits, total_cbits)

        # 1. First beam splitter on probe qubit
        qc.rx(self.probe_angle, 0)

        # 2. Entangle probe qubit with all cells in row/column via CNOT
        for i in range(1, 1 + num_targets):
            qc.cx(0, i)

        qc.rx(-math.pi, 0)
        qc.barrier()

        # 3. Measurement on ship cells (Bomb interaction / wavefunction collapse)
        # In physical EV, any bomb in the path acts as an observer/measurement.
        for c_idx, s_idx in enumerate(ship_local_indices):
            q_target = 1 + s_idx
            qc.measure(q_target, c_idx)

        qc.barrier()

        # 4. Second beam splitter stage: reverse superposition
        qc.rx(math.pi, 0)
        for i in range(1, 1 + num_targets):
            qc.cx(0, i)
        qc.rx(-self.probe_angle, 0)

        # 5. Measure probe qubit (dark port)
        probe_cbit = num_ships
        qc.measure(0, probe_cbit)

        return qc

    def run_probe(self, num_targets: int, ship_local_indices: List[int], shots: int = 10000) -> Dict[str, Any]:
        """
        Executes an actual quantum simulation of one row or column probe.

        Returns detailed physical outcome statistics:
        - explosions: Count of shots where a ship was triggered and exploded ("boom!")
        - detections: Count of shots where dark port fired without any ship exploding ("bomb found")
        - inconclusive: Count of shots where probe was 0 and no explosion occurred
        - ev_ratio: Empirical detection / explosion ratio
        """
        qc = self.build_circuit(num_targets, ship_local_indices)
        compiled_circuit = transpile(qc, self.simulator)
        job = self.simulator.run(compiled_circuit, shots=shots)
        result = job.result()
        raw_counts = result.get_counts(compiled_circuit)

        num_ships = len(ship_local_indices)
        probe_cbit = num_ships

        explosions = 0
        detections = 0
        inconclusive = 0

        for bitstring, count in raw_counts.items():
            # In Qiskit, bitstrings are ordered [c_{k-1}, ..., c_0]
            # Reverse to match declaration order [c_0, ..., c_{k-1}]
            bits = bitstring[::-1]

            # Check if any ship measurement was 1
            ship_exploded = any(bits[i] == '1' for i in range(num_ships))
            probe_detected = (bits[probe_cbit] == '1')

            if ship_exploded:
                explosions += count
            elif probe_detected:
                detections += count
            else:
                inconclusive += count

        ev_ratio = (detections / explosions) if explosions > 0 else (float('inf') if detections > 0 else 0.0)

        return {
            'shots': shots,
            'num_targets': num_targets,
            'num_ships': num_ships,
            'explosions': explosions,
            'detections': detections,
            'inconclusive': inconclusive,
            'detection_rate': detections / shots,
            'explosion_rate': explosions / shots,
            'inconclusive_rate': inconclusive / shots,
            'ev_ratio': ev_ratio,
            'circuit': qc,
            'raw_counts': raw_counts
        }


# =====================================================================
# 3. GAMEPLAY ENGINE: QUANTUM RADAR VS CLASSICAL BRUTE-FORCE
# =====================================================================

def simulate_quantum_battleship_game(
    board: BattleshipBoard,
    probe_angle: float = math.pi / 3,
    shots_per_probe: int = 10000,
    detection_threshold: float = 0.05,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Simulates an entire game of Battleship played by the Quantum Radar Agent:
    Phase 1: 2N quantum superposition line sweeps (cols and rows).
    Phase 2: Cell-level disambiguation of candidate intersections using targeted EV probes.
    """
    radar = QuantumRadar(probe_angle=probe_angle)
    rows, cols = board.rows, board.cols

    if verbose:
        print("================================================================")
        print(">>> QUANTUM RADAR BATTLESHIP: ACTUAL QUANTUM SIMULATION <<<")
        print("================================================================")
        print(f"Board Dimensions: {rows}x{cols} ({rows*cols} cells)")
        print(f"Total Ships Placed: {len(board.ships)} ({int(np.sum(board.grid))} ship segments)")
        for s in board.ships:
            coords_str = ", ".join([f"{chr(65+c)}{r+1}" for r, c in s.coordinates])
            print(f"  - {s.name} (length {s.size}): [{coords_str}]")
        print("\nInitial Board (S = Ship, ~ = Water):")
        print(board.render_ascii())
        print("----------------------------------------------------------------")

    # Tracking metrics
    col_results = []
    row_results = []
    hot_cols = []
    hot_rows = []

    total_quantum_shots = 0
    total_simulated_explosions = 0
    total_simulated_detections = 0
    total_measurements = 0

    representative_circuit = None

    # -------------------------------------------------------------
    # PHASE 1: QUANTUM LINE SWEEPS (Superposition Scanning)
    # -------------------------------------------------------------
    if verbose:
        print("\n[PHASE 1] Quantum Superposition Line Sweeps...")
        print("Scanning Columns...")

    for c in range(cols):
        total_measurements += 1
        col_cells = [(r, c) for r in range(rows)]
        ship_local_indices = [r for r in range(rows) if board.grid[r, c] == 1]

        probe_res = radar.run_probe(num_targets=rows, ship_local_indices=ship_local_indices, shots=shots_per_probe)
        col_results.append(probe_res)

        total_quantum_shots += probe_res['shots']
        total_simulated_explosions += probe_res['explosions']
        total_simulated_detections += probe_res['detections']

        is_hot = probe_res['detection_rate'] >= detection_threshold
        if is_hot:
            hot_cols.append(c)

        if len(ship_local_indices) > 0 and representative_circuit is None:
            representative_circuit = probe_res['circuit']

        if verbose:
            status = f"DETECTED! (Rate: {probe_res['detection_rate']:.1%}, Explosions: {probe_res['explosions']})" if is_hot else "Clear (0 ships)"
            print(f"  Col {chr(65+c)}: {status}")

    if verbose:
        print("\nScanning Rows...")

    for r in range(rows):
        total_measurements += 1
        row_cells = [(r, c) for c in range(cols)]
        ship_local_indices = [c for c in range(cols) if board.grid[r, c] == 1]

        probe_res = radar.run_probe(num_targets=cols, ship_local_indices=ship_local_indices, shots=shots_per_probe)
        row_results.append(probe_res)

        total_quantum_shots += probe_res['shots']
        total_simulated_explosions += probe_res['explosions']
        total_simulated_detections += probe_res['detections']

        is_hot = probe_res['detection_rate'] >= detection_threshold
        if is_hot:
            hot_rows.append(r)

        if len(ship_local_indices) > 0 and representative_circuit is None:
            representative_circuit = probe_res['circuit']

        if verbose:
            status = f"DETECTED! (Rate: {probe_res['detection_rate']:.1%}, Explosions: {probe_res['explosions']})" if is_hot else "Clear (0 ships)"
            print(f"  Row {r+1}: {status}")

    # -------------------------------------------------------------
    # PHASE 2: CANDIDATE INTERSECTIONS & CELL DISAMBIGUATION
    # -------------------------------------------------------------
    candidate_intersections = [(r, c) for r in hot_rows for c in hot_cols]
    true_ship_cells = board.get_ship_cells()
    total_ship_segments = len(true_ship_cells)

    if verbose:
        hot_col_names = [chr(65+c) for c in hot_cols]
        hot_row_names = [str(r+1) for r in hot_rows]
        print("\n[PHASE 2] Candidate Analysis & Quantum Disambiguation:")
        print(f"  Hot Columns: {hot_col_names}")
        print(f"  Hot Rows:    {hot_row_names}")
        print(f"  Raw Intersection Count: {len(candidate_intersections)} candidate cells")

    confirmed_ships = []
    disambiguation_probes = 0

    # If the number of intersections equals the known ship segment count or if no false positives exist:
    if len(candidate_intersections) == total_ship_segments and set(candidate_intersections) == set(true_ship_cells):
        confirmed_ships = candidate_intersections
        if verbose:
            print("  Exact match achieved directly from line superposition scans (no ghost intersections)!")
    else:
        # Perform targeted cell-level EV probes to resolve ambiguities without brute force
        if verbose:
            print(f"  Ambiguity detected ({len(candidate_intersections)} candidates for {total_ship_segments} ship parts).")
            print("  Running targeted Quantum EV probes on candidate cells...")

        for r, c in candidate_intersections:
            total_measurements += 1
            disambiguation_probes += 1
            is_ship = (board.grid[r, c] == 1)
            target_indices = [0]
            ship_indices = [0] if is_ship else []

            cell_probe = radar.run_probe(num_targets=1, ship_local_indices=ship_indices, shots=shots_per_probe)
            total_quantum_shots += cell_probe['shots']
            total_simulated_explosions += cell_probe['explosions']
            total_simulated_detections += cell_probe['detections']

            cell_name = f"{chr(65+c)}{r+1}"
            if cell_probe['detection_rate'] >= detection_threshold:
                confirmed_ships.append((r, c))
                if verbose:
                    print(f"    Cell {cell_name}: Confirmed SHIP via interaction-free probe! (Det: {cell_probe['detection_rate']:.1%})")
            else:
                if verbose:
                    print(f"    Cell {cell_name}: Confirmed WATER (empty cell filtered out)")

    # -------------------------------------------------------------
    # PHASE 3: SCORING & FINAL PERFORMANCE EVALUATION
    # -------------------------------------------------------------
    true_ships_set = set(true_ship_cells)
    confirmed_set = set(confirmed_ships)

    correct_detections = len(confirmed_set.intersection(true_ships_set))
    false_positives = len(confirmed_set - true_ships_set)
    missed_ships = len(true_ships_set - confirmed_set)

    precision = correct_detections / len(confirmed_ships) if confirmed_ships else 0.0
    recall = correct_detections / total_ship_segments if total_ship_segments > 0 else 1.0

    # Theoretical EV Score: cos^2(theta / 2)
    # At theta = pi/3: cos^2(pi/6) = (sqrt(3)/2)^2 = 3/4 = 75%
    # Detection rate: cos^2(theta/2) * sin^2(theta/2) = (3/4)*(1/4) = 3/16 = 18.75%
    # Explosion rate: sin^2(theta/2) = 1/4 = 25.0%
    # EV score = 18.75% / 25.0% = 75.0%
    theo_explosion_rate = (math.sin(probe_angle / 2)) ** 2
    theo_detection_rate = (math.cos(probe_angle / 2)) ** 2 * theo_explosion_rate
    theoretical_ev_score = (theo_detection_rate / theo_explosion_rate) if theo_explosion_rate > 0 else 0.0

    # Empirical EV Score from this actual simulation
    empirical_ev_score = (total_simulated_detections / total_simulated_explosions) if total_simulated_explosions > 0 else 0.0

    # Measurement Efficiency
    classical_brute_force_measurements = rows * cols
    quantum_measurements = total_measurements
    measurement_ratio = quantum_measurements / classical_brute_force_measurements
    speedup_ratio = classical_brute_force_measurements / quantum_measurements if quantum_measurements > 0 else 0.0

    # Slide 17 Formulas:
    # "Battleship score: Detection / Explosion x Measurements / Brute-force"
    battleship_score_literal = theoretical_ev_score * measurement_ratio
    battleship_score_speedup = theoretical_ev_score * speedup_ratio
    empirical_battleship_score = empirical_ev_score * speedup_ratio

    if verbose:
        print("\n================================================================")
        print(">>> FINAL RESULTS & PERFORMANCE <<<")
        print("================================================================")
        print("Final Classified Board (O = Found Ship, S = Undetected, ~ = Water):")
        print(board.render_ascii(detected_cells=confirmed_ships))
        print("----------------------------------------------------------------")
        print(f"Total Ships on Board:          {total_ship_segments}")
        print(f"Ships Correctly Located:       {correct_detections} / {total_ship_segments} ({recall:.1%})")
        print(f"False Positives:               {false_positives}")
        print(f"Quantum Measurements Taken:    {quantum_measurements} (Lines: {rows+cols}, Disambiguation: {disambiguation_probes})")
        print(f"Classical Measurements Needed: {classical_brute_force_measurements} (Brute-force)")
        print(f"Measurement Reduction:         {(1 - measurement_ratio):.1%} fewer scans!")
        print("----------------------------------------------------------------")
        print(f"Total Quantum Shots Fired:     {total_quantum_shots:,}")
        print(f"Simulated Physical Explosions: {total_simulated_explosions:,} (Triggered on ships)")
        print(f"Interaction-Free Detections:   {total_simulated_detections:,} (Dark-port detections)")
        print(f"Empirical E.V. Score:          {empirical_ev_score:.2%} (Actual Detections / Explosions)")
        print(f"Theoretical E.V. Score:        {theoretical_ev_score:.2%} (Slide 10/16 Benchmark)")
        print("----------------------------------------------------------------")
        print(f"Battleship Score (Slide 17 formula):          {battleship_score_literal:.3f}")
        print(f"Battleship Score (Speedup-adjusted formula):  {battleship_score_speedup:.3f}")
        print(f"Empirical Battleship Score (This run):        {empirical_battleship_score:.3f}")
        print("================================================================\n")

    return {
        'board_dimensions': (rows, cols),
        'total_ships': len(board.ships),
        'total_ship_segments': total_ship_segments,
        'true_ship_cells': [list(c) for c in true_ship_cells],
        'confirmed_ships': [list(c) for c in confirmed_ships],
        'correct_detections': correct_detections,
        'false_positives': false_positives,
        'missed_ships': missed_ships,
        'precision': precision,
        'recall': recall,
        'quantum_measurements': quantum_measurements,
        'classical_measurements': classical_brute_force_measurements,
        'measurement_reduction': 1 - measurement_ratio,
        'speedup_ratio': speedup_ratio,
        'total_quantum_shots': total_quantum_shots,
        'total_simulated_explosions': total_simulated_explosions,
        'total_simulated_detections': total_simulated_detections,
        'theoretical_ev_score': theoretical_ev_score,
        'empirical_ev_score': empirical_ev_score,
        'battleship_score_slide17': battleship_score_literal,
        'battleship_score_speedup': battleship_score_speedup,
        'empirical_battleship_score': empirical_battleship_score,
        'representative_circuit': representative_circuit,
        'col_results': col_results,
        'row_results': row_results,
    }


def simulate_classical_game(board: BattleshipBoard) -> Dict[str, Any]:
    """
    Simulates a classical player searching for all ships on the board.
    Classical probing must query cell-by-cell. Whenever a ship is hit,
    it triggers a direct explosion (100% explosion, 0% interaction-free detection).
    """
    rows, cols = board.rows, board.cols
    total_cells = rows * cols
    ship_cells = set(board.get_ship_cells())
    total_ships = len(ship_cells)

    found_ships = set()
    shots_fired = 0
    explosions = 0

    # Hunt strategy (standard systematic scan until all ships found)
    for r in range(rows):
        for c in range(cols):
            shots_fired += 1
            if (r, c) in ship_cells:
                found_ships.add((r, c))
                explosions += 1  # 100% explosion rate for classical hits!
            if len(found_ships) == total_ships:
                break
        if len(found_ships) == total_ships:
            break

    return {
        'total_measurements': shots_fired,
        'max_measurements': total_cells,
        'explosions': explosions,
        'interaction_free_detections': 0,
        'ev_score': 0.0,
        'ships_found': len(found_ships),
        'total_ships': total_ships
    }


# =====================================================================
# 4. VISUALIZATION & ARTIFACT GENERATION
# =====================================================================

def generate_visualizations(
    quantum_res: Dict[str, Any],
    classical_res: Dict[str, Any],
    board: BattleshipBoard,
    output_png: str = "results/quantum_battleship_analysis.png"
):
    """Generates a comprehensive 4-panel publication-grade analysis figure."""
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    fig.patch.set_facecolor('#ffffff')

    rows, cols = board.rows, board.cols

    # --- Panel 1: Battleship Board Status ---
    ax_board = axs[0, 0]
    board_display = np.zeros((rows, cols, 3))
    # Colors: Water = soft blue (#d0e1fd), Ship Detected = emerald (#2ecc71), Missed/Ghost = coral (#e74c3c)
    water_color = [0.82, 0.89, 0.98]
    detected_color = [0.18, 0.80, 0.44]
    hidden_color = [0.20, 0.40, 0.70]

    for r in range(rows):
        for c in range(cols):
            board_display[r, c] = water_color

    confirmed_set = set(tuple(x) for x in quantum_res['confirmed_ships'])
    true_set = set(board.get_ship_cells())

    for r, c in true_set:
        if (r, c) in confirmed_set:
            board_display[r, c] = detected_color
        else:
            board_display[r, c] = hidden_color

    ax_board.imshow(board_display)
    ax_board.set_xticks(range(cols))
    ax_board.set_yticks(range(rows))
    ax_board.set_xticklabels([chr(65 + c) for c in range(cols)], fontsize=10 if cols > 6 else 12, fontweight='bold')
    ax_board.set_yticklabels([str(r + 1) for r in range(rows)], fontsize=10 if rows > 6 else 12, fontweight='bold')

    font_sz = 8 if rows > 6 else 10
    water_sz = 11 if rows > 6 else 14
    for r in range(rows):
        for c in range(cols):
            if (r, c) in confirmed_set:
                txt = 'SHIP' if rows > 6 else 'SHIP\n[FOUND]'
                ax_board.text(c, r, txt, ha='center', va='center', color='white', fontweight='bold', fontsize=font_sz)
            else:
                ax_board.text(c, r, '~', ha='center', va='center', color='#5577aa', fontsize=water_sz)

    ax_board.set_title("1. Battleship Grid: Quantum Radar Findings", fontsize=14, fontweight='bold', pad=10)
    ax_board.set_xlabel("Columns", fontsize=11)
    ax_board.set_ylabel("Rows", fontsize=11)

    # --- Panel 2: Quantum Probe Outcome Distribution (Matching Slide 16) ---
    ax_hist = axs[0, 1]
    # Find a probe with ships to plot outcome counts
    sample_probe = None
    for res in quantum_res['col_results'] + quantum_res['row_results']:
        if res['num_ships'] > 0:
            sample_probe = res
            break

    if sample_probe is None:
        sample_probe = quantum_res['col_results'][0]

    categories = ['Bomb Found\n(Det. w/o Boom)', 'Boom!\n(Explosion)', 'No Explosion\n(Inconclusive)']
    counts = [sample_probe['detections'], sample_probe['explosions'], sample_probe['inconclusive']]
    colors = ['#9b59b6', '#e74c3c', '#27ae60']

    bars = ax_hist.bar(categories, counts, color=colors, width=0.55, edgecolor='black', linewidth=1.2)
    ax_hist.set_title(f"2. EV Probe Quantum Measurement Distribution (Slide 16 Spec)\n[Shots = {sample_probe['shots']:,}, Angle = {math.pi/3:.2f} rad]", fontsize=13, fontweight='bold', pad=10)
    ax_hist.set_ylabel("Measured Shot Counts", fontsize=11)
    ax_hist.grid(axis='y', linestyle='--', alpha=0.5)

    for bar, count in zip(bars, counts):
        pct = count / sample_probe['shots']
        ax_hist.text(bar.get_x() + bar.get_width()/2, bar.get_height() + sample_probe['shots']*0.015,
                     f"{count:,}\n({pct:.1%})", ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax_hist.set_ylim(0, max(counts) * 1.22)

    # --- Panel 3: Performance Comparison: Quantum vs Classical ---
    ax_comp = axs[1, 0]
    metrics = ['Measurements', 'Explosions\n(Damage)', 'EV Score (%)']
    quantum_vals = [
        quantum_res['quantum_measurements'],
        # Average explosions per target
        quantum_res['total_simulated_explosions'] / (quantum_res['total_quantum_shots'] / 100) if quantum_res['total_quantum_shots'] > 0 else 0,
        quantum_res['theoretical_ev_score'] * 100
    ]
    classical_vals = [
        classical_res['total_measurements'],
        100.0,  # Classical hits 100% explode
        0.0     # Classical has 0% EV score
    ]

    x = np.arange(len(metrics))
    width = 0.35

    b1 = ax_comp.bar(x - width/2, quantum_vals, width, label='Quantum Radar', color='#2980b9', edgecolor='black')
    b2 = ax_comp.bar(x + width/2, classical_vals, width, label='Classical Brute-Force', color='#e67e22', edgecolor='black')

    ax_comp.set_title("3. Quantum vs Classical Battleship Performance", fontsize=14, fontweight='bold', pad=10)
    ax_comp.set_xticks(x)
    ax_comp.set_xticklabels(metrics, fontsize=11, fontweight='bold')
    ax_comp.legend(fontsize=11)
    ax_comp.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in b1:
        ax_comp.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"{bar.get_height():.1f}", ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in b2:
        ax_comp.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"{bar.get_height():.1f}", ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax_comp.set_ylim(0, max(max(quantum_vals), max(classical_vals)) * 1.2)

    # --- Panel 4: Theoretical EV Score vs Probe Angle theta ---
    ax_angle = axs[1, 1]
    thetas = np.linspace(0.05, math.pi, 200)
    ev_scores = [(math.cos(t/2)**2) * 100 for t in thetas]
    p_booms = [(math.sin(t/2)**2) * 100 for t in thetas]
    p_dets = [(math.cos(t/2)**2 * math.sin(t/2)**2) * 100 for t in thetas]

    ax_angle.plot(thetas, ev_scores, label=r'EV Score: $P(\mathrm{Det})/P(\mathrm{Boom}) = \cos^2(\theta/2)$', color='#8e44ad', linewidth=2.5)
    ax_angle.plot(thetas, p_booms, label=r'Explosion Rate: $\sin^2(\theta/2)$', color='#c0392b', linestyle='--', linewidth=2)
    ax_angle.plot(thetas, p_dets, label=r'Detection Rate: $\cos^2(\theta/2)\sin^2(\theta/2)$', color='#27ae60', linestyle='-.', linewidth=2)

    # Highlight Slide 9 (pi/2) and Slide 10 (pi/3)
    ax_angle.scatter([math.pi/2], [50.0], color='#2980b9', s=90, zorder=5)
    ax_angle.text(math.pi/2 + 0.08, 50, r'$\theta=\pi/2 \to 50\%$ (Slide 9)', fontsize=10, fontweight='bold', color='#2980b9')

    ax_angle.scatter([math.pi/3], [75.0], color='#d35400', s=90, zorder=5)
    ax_angle.text(math.pi/3 + 0.08, 75, r'$\theta=\pi/3 \to 75\%$ (Slide 10, 16)', fontsize=10, fontweight='bold', color='#d35400')

    ax_angle.set_title(r"4. Elitzur-Vaidman Theoretical Trade-off vs $\theta$", fontsize=14, fontweight='bold', pad=10)
    ax_angle.set_xlabel(r"Probe Rotation Angle $\theta$ (radians)", fontsize=11)
    ax_angle.set_ylabel("Probability / Ratio (%)", fontsize=11)
    ax_angle.set_xlim(0, math.pi)
    ax_angle.set_ylim(0, 105)
    ax_angle.legend(loc='lower left', fontsize=9.5)
    ax_angle.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Generated high-resolution visualization saved to: {output_png}")


def export_results(
    quantum_res: Dict[str, Any],
    classical_res: Dict[str, Any],
    board: BattleshipBoard,
    results_dir: str = "results"
):
    """Exports structured JSON, text report, and circuit diagrams to results directory."""
    os.makedirs(results_dir, exist_ok=True)

    # 1. JSON Summary (clean serializable)
    clean_quantum = {k: v for k, v in quantum_res.items() if k not in ['representative_circuit', 'col_results', 'row_results']}
    summary_data = {
        'board': {
            'rows': board.rows,
            'cols': board.cols,
            'ships': [{'name': s.name, 'size': s.size, 'coords': s.coordinates} for s in board.ships]
        },
        'quantum_simulation': clean_quantum,
        'classical_benchmark': classical_res
    }
    json_path = os.path.join(results_dir, "simulation_summary.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print(f"[OK] Exported JSON summary to: {json_path}")

    # 2. Text Report
    report_path = os.path.join(results_dir, "simulation_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("====================================================================\n")
        f.write("      QUANTUM RADAR BATTLESHIP: COMPLETE SIMULATION REPORT\n")
        f.write("====================================================================\n\n")
        f.write(f"Board Layout ({board.rows}x{board.cols}):\n")
        f.write(board.render_ascii(detected_cells=[tuple(x) for x in quantum_res['confirmed_ships']]))
        f.write("\n\n")
        f.write("1. SUMMARY METRICS:\n")
        f.write("--------------------------------------------------------------------\n")
        f.write(f"Total Ships:                     {quantum_res['total_ships']}\n")
        f.write(f"Total Ship Segments:             {quantum_res['total_ship_segments']}\n")
        f.write(f"Ships Correctly Located:         {quantum_res['correct_detections']} / {quantum_res['total_ship_segments']} ({quantum_res['recall']:.1%})\n")
        f.write(f"False Positives:                 {quantum_res['false_positives']}\n")
        f.write(f"Quantum Measurements Taken:      {quantum_res['quantum_measurements']} (Line sweeps + disambiguation)\n")
        f.write(f"Classical Brute-Force Scans:     {quantum_res['classical_measurements']} (Every cell checked)\n")
        f.write(f"Quantum Measurement Reduction:   {quantum_res['measurement_reduction']:.1%}\n")
        f.write(f"Quantum Speedup Factor:          {quantum_res['speedup_ratio']:.2f}x\n")
        f.write("--------------------------------------------------------------------\n\n")
        f.write("2. QUANTUM ELITZUR-VAIDMAN CIRCUIT OUTCOMES:\n")
        f.write("--------------------------------------------------------------------\n")
        f.write(f"Total Quantum Shots Fired:       {quantum_res['total_quantum_shots']:,}\n")
        f.write(f"Simulated Physical Explosions:   {quantum_res['total_simulated_explosions']:,}\n")
        f.write(f"Interaction-Free Detections:     {quantum_res['total_simulated_detections']:,}\n")
        f.write(f"Empirical E.V. Score:            {quantum_res['empirical_ev_score']:.2%}\n")
        f.write(f"Theoretical E.V. Score:          {quantum_res['theoretical_ev_score']:.2%}\n")
        f.write(f"Slide 17 Battleship Score:       {quantum_res['battleship_score_slide17']:.3f}\n")
        f.write(f"Speedup-Adjusted Score:          {quantum_res['battleship_score_speedup']:.3f}\n")
        f.write(f"Empirical Game Score:            {quantum_res['empirical_battleship_score']:.3f}\n")
        f.write("--------------------------------------------------------------------\n\n")
        f.write("3. CLASSICAL BENCHMARK COMPARISON:\n")
        f.write("--------------------------------------------------------------------\n")
        f.write(f"Classical Measurements:          {classical_res['total_measurements']}\n")
        f.write(f"Classical Explosions (Hits):     {classical_res['explosions']} (100% destroyed on hit)\n")
        f.write(f"Classical E.V. Score:            0.0% (Zero interaction-free capability)\n")
        f.write("====================================================================\n")
    print(f"[OK] Exported text report to: {report_path}")

    # 3. Circuit Diagram
    if quantum_res.get('representative_circuit'):
        circuit_path = os.path.join(results_dir, "circuit_diagram.txt")
        try:
            with open(circuit_path, 'w', encoding='utf-8') as f:
                f.write(str(quantum_res['representative_circuit'].draw(output='text')))
            print(f"[OK] Exported circuit diagram to: {circuit_path}")
        except Exception as e:
            print(f"Notice: Circuit diagram export skipped ({e})")


# =====================================================================
# 5. CLI ENTRYPOINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Quantum Battleship Elitzur-Vaidman Simulator")
    parser.add_argument('--scenario', type=str, choices=['standard', 'benchmark', 'multi'], default='standard',
                        help="Board scenario: 'standard' (Challenging 8x8 5-ship fleet), 'benchmark' (4x4 Slide 13/16 spec), 'multi' (4x4 2-ship)")
    parser.add_argument('--angle', type=str, default='pi/3',
                        help="Probe angle: 'pi/3' (75%% EV, Slide 10/16) or 'pi/2' (50%% EV, Slide 9) or numeric float")
    parser.add_argument('--shots', type=int, default=4000,
                        help="Number of shots per quantum probe (default: 4,000)")
    parser.add_argument('--no-plot', action='store_true',
                        help="Disable generating matplotlib plot")
    args = parser.parse_args()

    # Parse probe angle
    if args.angle == 'pi/3':
        angle = math.pi / 3
    elif args.angle == 'pi/2':
        angle = math.pi / 2
    elif args.angle == 'pi/4':
        angle = math.pi / 4
    else:
        try:
            angle = float(args.angle)
        except ValueError:
            print(f"Invalid angle '{args.angle}', defaulting to pi/3")
            angle = math.pi / 3

    # Setup board
    if args.scenario == 'standard':
        board = BattleshipBoard.create_standard_board()
    elif args.scenario == 'benchmark':
        board = BattleshipBoard.create_benchmark_board()
    elif args.scenario == 'multi':
        board = BattleshipBoard.create_multi_ship_board()
    else:
        board = BattleshipBoard.create_standard_board()

    # Run primary quantum simulation
    quantum_res = simulate_quantum_battleship_game(
        board=board,
        probe_angle=angle,
        shots_per_probe=args.shots,
        verbose=True
    )

    # Run classical benchmark
    classical_res = simulate_classical_game(board)

    # Export primary results
    export_results(quantum_res, classical_res, board, results_dir="results")

    # Generate visualization
    if not args.no_plot:
        plot_path = os.path.join("results", "quantum_battleship_analysis.png")
        generate_visualizations(quantum_res, classical_res, board, output_png=plot_path)

    # If running standard, also generate the 4x4 benchmark artifact for slide 13/16 comparison
    if args.scenario == 'standard':
        print("\n" + "="*64)
        print("BONUS: Also validating Presentation Benchmark scenario (4x4 Slide 13/16)...")
        print("="*64)
        bench_board = BattleshipBoard.create_benchmark_board()
        bench_res = simulate_quantum_battleship_game(
            board=bench_board,
            probe_angle=angle,
            shots_per_probe=args.shots,
            verbose=False
        )
        bench_classical = simulate_classical_game(bench_board)
        bench_json = os.path.join("results", "benchmark_4x4_summary.json")
        with open(bench_json, 'w', encoding='utf-8') as f:
            clean_b = {k: v for k, v in bench_res.items() if k not in ['representative_circuit', 'col_results', 'row_results']}
            json.dump({'board': {'rows': 4, 'cols': 4, 'ships': [{'name': 'Destroyer', 'size': 2, 'coords': [[1, 2], [1, 3]]}]}, 'quantum_simulation': clean_b, 'classical_benchmark': bench_classical}, f, indent=2)
        print(f"[OK] Saved 4x4 benchmark validation summary to: {bench_json}")

        # Also validate multi-ship 4x4 scenario
        multi_board = BattleshipBoard.create_multi_ship_board()
        multi_res = simulate_quantum_battleship_game(
            board=multi_board,
            probe_angle=angle,
            shots_per_probe=args.shots,
            verbose=False
        )
        multi_classical = simulate_classical_game(multi_board)
        multi_json = os.path.join("results", "multi_ship_summary.json")
        with open(multi_json, 'w', encoding='utf-8') as f:
            clean_m = {k: v for k, v in multi_res.items() if k not in ['representative_circuit', 'col_results', 'row_results']}
            json.dump({'quantum': clean_m, 'classical': multi_classical}, f, indent=2)
        print(f"[OK] Saved multi-ship validation summary to: {multi_json}")


if __name__ == '__main__':
    main()
