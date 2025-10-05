import numpy as np
import math
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator  
from qiskit.visualization import plot_histogram

# ---Function to run one E-V "probe" on a row or column ---
def run_ev_probe(num_targets, angle, shots=1024):
    """
    Creates and runs an Elitzur-Vaidman circuit to check for "bombs".

    Args:
        num_targets (int): The number of squares in the row/col that have ships.
        angle (float): The rotation angle for the Rx gates.
        shots (int): The number of times to run the simulation.

    Returns:
        dict: A dictionary containing the measurement counts.
    """
    if num_targets == 0:
        # If there are no ships, there's nothing to detect.
        return {'0': shots, '1': 0}

    qc = QuantumCircuit(2, 1)
    qc.rx(angle, 0)
    qc.cx(0, 1)
    qc.rx(-angle, 0)
    qc.measure(0, 0)

    # --- Simulation ---
    simulator = AerSimulator()  
    compiled_circuit = transpile(qc, simulator)
    job = simulator.run(compiled_circuit, shots=shots)
    result = job.result()
    counts = result.get_counts(compiled_circuit)

    return counts


# --- Main Orchestration and Testing ---
# --- Main Orchestration and Testing ---
if __name__ == '__main__':
    # -------------------------------------------------------------
    # 1. SETUP THE GAME
    # -------------------------------------------------------------
    board = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

    rows, cols = board.shape
    probe_angle = math.pi / 3
    shots_per_probe = 4096

    print("--- 🚢 Quantum Battleship ---")
    print("Board Layout:")
    print(board, "\n")

    # -------------------------------------------------------------
    # 2. RUN THE QUANTUM SCAN
    # -------------------------------------------------------------
    hot_rows = [False] * rows
    hot_cols = [False] * cols
    total_simulated_explosions = 0

    # --- Scan Columns ---
    print("Scanning Columns...")
    for c in range(cols):
        num_ships_in_col = np.sum(board[:, c])
        if num_ships_in_col > 0:
            counts = run_ev_probe(num_ships_in_col, probe_angle, shots_per_probe)
            if counts.get('1', 0) > 0:
                hot_cols[c] = True
                print(f"  Column {c}: Ship detected!")
                prob_boom = (math.sin(probe_angle / 2))**2
                total_simulated_explosions += prob_boom * num_ships_in_col

    # --- Scan Rows ---
    print("\nScanning Rows...")
    for r in range(rows):
        num_ships_in_row = np.sum(board[r, :])
        if num_ships_in_row > 0:
            counts = run_ev_probe(num_ships_in_row, probe_angle, shots_per_probe)
            if counts.get('1', 0) > 0:
                hot_rows[r] = True
                print(f"  Row {r}: Ship detected!")
                prob_boom = (math.sin(probe_angle / 2))**2
                total_simulated_explosions += prob_boom * num_ships_in_row

    # -------------------------------------------------------------
    # 3. CALCULATE RESULTS
    # -------------------------------------------------------------
    found_ships = []
    for r in range(rows):
        for c in range(cols):
            if hot_rows[r] and hot_cols[c]:
                found_ships.append((r, c))

    print("\n--- 🎯 Results ---")
    print(f"Ship locations identified at: {found_ships}")

    # --- Calculate the Final Score ---
    total_ship_parts = int(np.sum(board))
    detection_count = len([ship for ship in found_ships if board[ship[0], ship[1]] == 1])

    if total_ship_parts == 0:
        ev_score = 0
        battleship_score = 0
        empirical_score = 0
    else:
        # Theoretical E.V. Score
        explosion_rate = (math.sin(probe_angle / 2))**2
        detection_rate = 1 - explosion_rate
        ev_score = detection_rate / explosion_rate if explosion_rate > 0 else float('inf')
        
        # Final Battleship Score
        brute_force_measurements = rows * cols
        total_measurements = rows + cols
        efficiency_score = total_measurements / brute_force_measurements
        battleship_score = ev_score * (1/efficiency_score)
        empirical_score = detection_count / total_simulated_explosions if total_simulated_explosions > 0 else float('inf')


    print("\n--- 📊 Performance ---")
    print(f"Total Ships on Board: {total_ship_parts}")
    print(f"Ships Correctly Located: {detection_count}")
    print(f"Quantum Measurements: {rows + cols} (vs. {rows*cols} for classical)")
    print("---------------------------------")
    print(f"Theoretical E.V. Score (Circuit Quality): {ev_score:.2f}")
    print(f"Final Battleship Score (per problem spec): {battleship_score:.2f}")
    print(f"Empirical Score (This Game's Result): {empirical_score:.2f}")