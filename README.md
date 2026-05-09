# 🔬 Formal Methods Analysis Tool

A complete, functional Python-based application using **Streamlit** to perform formal feature model analysis and feature-to-code impact analysis. 

This tool is designed to bridge the gap between abstract feature models and actual software implementation by providing automated parsing, logical analysis, constraint verification, and dependency impact analysis.

---

## 👥 Group Members
- **Faez Ahmed** (23i-0598)
- **Hussnain Haider** (23i-0695)
- **Uzair Majeed** (23i-3063)

---

## ✨ Key Features

- **📄 XML Input & Logic Translation**: Automatically parses XML-based feature models and translates them into formal propositional logic and CNF clauses.
- **⚡ SAT-Based MWP Identification**: Utilizes an underlying SAT solver to identify Minimum Working Products (MWPs) that satisfy all feature model constraints.
- **🌳 Interactive Feature Tree**: Visually explore the feature hierarchy and verify constraints interactively. Select features to test if your configuration is valid.
- **💻 Codebase Mapping**: Map abstract features directly to source code files within your project repository.
- **🔗 Impact Analysis & Dependency Extraction**: Automated extraction of code dependencies to detect inconsistencies between formal feature model constraints and actual source code dependencies.
- **📊 Comprehensive Reporting**: Generates a detailed report summarizing the analysis, detected inconsistencies, and architectural violations.

---

## 🛠️ Technology Stack

- **Python 3.x**
- **[Streamlit](https://streamlit.io/)**: For the interactive web interface and dynamic dashboards.
- **[PySAT (python-sat)](https://pysathq.github.io/)**: For robust Boolean satisfiability solving and MWP calculation.
- **[NetworkX](https://networkx.org/) & [PyVis](https://pyvis.readthedocs.io/)**: For generating interactive, graph-based visualizations of feature trees and code dependencies.
- **[Pandas](https://pandas.pydata.org/)**: For data manipulation and mapping management.

---

## 🚀 Installation & Setup

1. **Clone or Download the Repository**
   Make sure you are in the project root directory.

2. **Install Dependencies**
   It is recommended to use a virtual environment. Install the required Python packages using:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   Launch the Streamlit server to open the application in your default web browser:
   ```bash
   python -m streamlit run app.py
   ```

---

## 📖 How to Use

1. **Upload Feature Model**: Navigate to the **XML Input & Logic** tab to upload your `feature-model.xml`.
2. **Review Formulas**: Check the generated propositional formulas and CNF clauses.
3. **Calculate MWP**: Go to the **MWP Results** tab to compute the Minimum Working Products using the SAT solver.
4. **Interactive Tree**: Use the **Feature Tree** tab to visualize the model and interactively select features to simulate a configuration.
5. **Code Mapping & Analysis**: Define feature-to-file mappings and run the **Impact Analysis** to see how feature selections impact the underlying codebase.
6. **Review Report**: Check the **Report** tab for a detailed breakdown of consistency checks and dependency validations.
