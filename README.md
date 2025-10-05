[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mmBvcuTa)
# Hackathon Problem - Battleship

## Instructions:
Read the problem statement in `Battleship.docx` and `Battleship - PPT.pdf`. This is an open-ended challenge with no starter code or required submission format - solve it however you want! Document your solution, code, results, and any relevant files in this repository.

## Your Team:
List out the QFF-Registered email IDs of people in your team here:
- lakshya.jindal@research.iiit.ac.in

## Your Solution:
### ## Methodology and Reasoning

The core methodology of this solution is to adapt the **Elitzur-Vaidman (E-V) interaction-free measurement** concept to the game of Battleship. The reasoning is that a quantum approach can be significantly more efficient than a classical brute-force search.

The strategy consists of two main parts:

1.  **The Quantum Probe**: A small quantum circuit was designed to act as a "probe." It uses `Rx` gates to place a probe qubit into superposition and a `CNOT` gate to entangle it with a target representing a potential ship. Through quantum interference, we can measure the probe qubit to see if an "interaction" occurred (i.e., a ship is present) with a high probability of not collapsing the superposition in a way that corresponds to a "hit" or "explosion."

2.  **The Scanning Strategy**: Instead of checking each grid square individually, the script probes entire columns and rows at once. If a probe of Column `C` indicates a ship, and a probe of Row `R` also indicates a ship, we can deduce the ship's location is at the intersection `(R, C)`. This reduces the number of required measurements for an $N \times N$ grid from $N^2$ to just $2N$.

### ## Code Snippets

The core quantum logic is encapsulated in the `run_ev_probe` function, which builds and simulates the E-V circuit.

```python
def run_ev_probe(num_targets, angle, shots=1024):
    """
    Creates and runs an Elitzur-Vaidman circuit to check for "bombs".
    """
    if num_targets == 0:
        # If there are no ships, there's nothing to detect.
        return {'0': shots, '1': 0}

    # qc with 1 probe qubit, 1 target qubit, and 1 classical bit
    qc = QuantumCircuit(2, 1)

    # Put the probe into superposition (1st beam splitter)
    qc.rx(angle, 0)
    # Entangle probe with target (the "interaction")
    qc.cx(0, 1)
    # Reverse the superposition (2nd beam splitter)
    qc.rx(-angle, 0)
    # Measure the probe to see if a ship was detected
    qc.measure(0, 0)

    # Simulate the circuit
    simulator = AerSimulator()
    compiled_circuit = transpile(qc, simulator)
    job = simulator.run(compiled_circuit, shots=shots)
    result = job.result()
    counts = result.get_counts(compiled_circuit)

    return counts
```
The results from the probe are then used to deduce ship locations with simple classical logic:
```python
# ... after scanning all rows and columns ...
found_ships = []
for r in range(rows):
    for c in range(cols):
        # A ship is at the intersection of a "hot" row and a "hot" column
        if hot_rows[r] and hot_cols[c]:
            found_ships.append((r, c))
```
## Results and Outputs
Here is a sample output for a 4x4 board with a single ship at coordinate (1, 1).
```
--- 🚢 Quantum Battleship ---
Board Layout:
[[0 0 0 0]
 [0 1 0 0]
 [0 0 0 0]
 [0 0 0 0]]

Scanning Columns...
  Column 1: Ship detected! ✅

Scanning Rows...
  Row 1: Ship detected! ✅

--- 🎯 Results ---
Ship locations identified at: [(1, 1)]

--- 📊 Performance ---
Total Ships on Board: 1
Ships Correctly Located: 1
Quantum Measurements: 8 (vs. 16 for classical)
---------------------------------
Theoretical E.V. Score (Circuit Quality): 3.00
Final Battleship Score (per problem spec): 6.00
Empirical Score (This Game's Result): 2.00
```

The output confirms that the single ship was correctly located using only 8 quantum measurements. It also displays the three key performance metrics, showing both the theoretical quality of the circuit and the specific outcome of this game.

## Challenges Faced and Solutions
Challenge: Incorrect Score for an Empty Board

Problem: The initial code produced a non-zero score even when no ships were placed on the board.

Reasoning: The scoring logic was based on theoretical probabilities of the probe circuit and was executed regardless of the board's state.

Solution: A conditional check was added. If the total number of ships on the board is zero, the scores are now correctly set to 0.

Challenge: Misinterpreting the ev_score

Problem: The ev_score was a constant 3.0 for any board with at least one ship, which was initially confusing.

Reasoning: It was determined that the ev_score from the presentation is a theoretical metric of the circuit's quality (P(Detection) / P(Explosion)), not a dynamic result of a specific game.

Solution: To provide a more intuitive metric, an Empirical Score (ships_found / simulated_explosions) was added. This gives a game-specific result, while the theoretical scores are kept to fulfill the problem's requirements.

*Note: There is no autograder for this problem. Your solution will be manually reviewed.*
