<p align="center">
  <img src="icon.png" alt="IMEI Generator Pro Icon" width="200" height="200">
</p>

<h1 align="center">IMEI Generator</h1>

<p align="center">
  <strong>A professional-grade, high-performance desktop utility for generating, validating, and managing IMEI numbers.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/UI-Custom_Tkinter-ff69b4?style=for-the-badge" alt="UI">
</p>

---

## ✨ Features

### 📡 Advanced Generation
- **Pattern & Mask Mode:** Use `X` as a wildcard (e.g., `35693803XXXXXX`) to generate IMEIs for specific ranges.
- **TAC-Based Generation:** Generate IMEIs using the 8-digit Type Allocation Code (TAC).
- **Sequential & Random Modes:** Toggle between predictable sequences or randomized batches.
- **Collision Handling:** Advanced logic ensures unique numbers within a single batch.

### 🔍 Batch Validation
- **Luhn Algorithm:** Rigorous checksum validation using ISO/IEC 7812-1 standard formulas.
- **Duplicate Detection:** Real-time identification and flagging of duplicate IMEIs in large lists.
- **Live Analytics:** Instant counters for Total, Valid, Invalid, and Duplicate entries.

### 🎨 Premium User Experience
- **Dynamic Theming:** Seamlessly switch between **Cyber Dark** and **Cream & Mocha** themes.
- **Zero Freeze UI:** Multi-threaded execution ensures the interface remains responsive during heavy batch processing.
- **Custom Widgets:** Hand-crafted rounded cards, glow buttons, and hover tooltips.

### 💾 Data Management
- **Smart Import:** Load IMEIs directly from `.txt` or `.csv` files.
- **Multi-Format Export:** Save results to `.txt`, `.csv` (Excel ready), or `.json`.
- **Session Tracking:** Dedicated history log to monitor all generation and validation activity.

---

## 📸 Screenshots

<p align="center">
  <img width="852" height="689" alt="Dark" src="https://github.com/user-attachments/assets/c8c023d2-9980-4880-a7f8-b26edf68ed1b" />
  <br>
  <em>Figure 1: Cyber Dark Theme - Modern, high-contrast interface for focused work.</em>
</p>

<p align="center">
  <img width="852" height="689" alt="Light" src="https://github.com/user-attachments/assets/0830f8e7-268f-412b-8cb3-e26516be6408" />
  <br>
  <em>Figure 2: Cream & Mocha Theme - Soft, elegant aesthetic for comfortable day-time use.</em>
</p>

---

## 🚀 Installation & Usage

### Option 1: Standalone Executable (Recommended)
Download the latest `imei_tool.exe` from the [Releases](https://github.com/not-GIANT/IMEI-Generator/releases) page. No Python installation required!

### Option 2: Run from Source
1. **Clone the Repo:**
   ```bash
   git clone https://github.com/not-GIANT/IMEI-Generator.git
   ```
2. **Launch:**
   ```bash
   python imei_tool.py
   ```

---

## 🛠 Tech Stack
- **Engine:** Python 3.13
- **GUI:** Custom Tkinter Framework
- **Security:** Luhn Algorithm (ISO/IEC 7812-1)
- **Deployment:** PyInstaller

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author
**Coded with ❤️ by GIANT**

If you find this tool useful, feel free to ⭐ the repository!
