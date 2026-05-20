# 📱 IMEI Generator

A professional-grade, high-performance desktop utility for generating, validating, and managing IMEI (International Mobile Equipment Identity) numbers. Built with a fully custom, modern Tkinter framework that delivers a sleek, responsive experience with **zero external dependencies**.

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows)

---

## ✨ Features

### 📡 Advanced Generation
- **Pattern & Mask Mode:** Use `X` as a wildcard (e.g., `35693803XXXXXX`) to generate IMEIs for specific ranges.
- **TAC-Based Generation:** Generate IMEIs using the 8-digit Type Allocation Code.
- **Sequential & Random Modes:** Toggle between predictable sequences or randomized batches.
- **Collision Handling:** Smart logic to ensure unique numbers within a single batch.

### 🔍 Batch Validation
- **Luhn Algorithm:** Rigorous checksum validation using industry-standard formulas.
- **Duplicate Detection:** Real-time identification of duplicate IMEIs in large lists.
- **Instant Stats:** Live counters for Total, Valid, Invalid, and Duplicate entries.

### 🎨 Premium User Experience
- **Dynamic Theming:** Instant switching between a sleek **Cyber Dark** mode and a warm **Cream & Mocha** light theme.
- **Threaded Execution:** Background processing ensures the UI never freezes, even when processing thousands of entries.
- **Custom UI Components:** Hand-crafted rounded cards, glow buttons, and hover tooltips for a modern "non-native" look.

### 💾 Data Management
- **Smart Import:** Load IMEIs directly from `.txt` or `.csv` files.
- **Multi-Format Export:** Save your results to `.txt`, `.csv` (Excel ready), or `.json`.
- **Session History:** A built-in log to track your activity across the current session.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher.
- No external libraries required (uses only standard library + Tkinter).

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/not-GIANT/IMEI-Generator.git
   ```
2. Run the application:
   ```bash
   python imei_tool.py
   ```

### Standalone Executable
You can also find the pre-compiled `.exe` in the [Releases](https://github.com/not-GIANT/IMEI-Generator/releases) section (no Python installation required).

---

## 🛠 Tech Stack
- **Language:** Python 3.13
- **GUI Framework:** Tkinter (Customized)
- **Algorithms:** Luhn (ISO/IEC 7812-1)
- **Packaging:** PyInstaller

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author
**GIANT** - *Lead Developer* - [GitHub Profile](https://github.com/not-GIANT)

---
