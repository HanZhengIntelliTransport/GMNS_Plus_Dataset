# Global_Dataset Environment Setup

This guide will help you set up the `Global_Dataset` Conda environment, install required dependencies, and run the project.

---

## 📦 1. Create and Activate Conda Environment

Open your terminal and run the following commands:

```bash
# Create a new conda environment named Global_Dataset with Python 3.12
conda create -n Global_Dataset python=3.12 -y

# Activate the environment
conda activate Global_Dataset
```

---

## 📚 2. Install Required Packages

Install the required Python packages using `pip`:

```bash
pip install pandas scikit-learn DTALite
```

If you prefer using `conda` for pandas and scikit-learn:

```bash
conda install pandas scikit-learn -y
pip install DTALite
```

---

## 🚀 3. Run Your Project

Now you're ready to run the project scripts:

```bash
python your_main_script.py
```

> Replace `your_main_script.py` with your actual entry file.

---

## 🧹 4. Deactivate and Remove Environment (Optional)

When you're done, you can deactivate or remove the environment:

```bash
# Deactivate
conda deactivate

# Remove the environment (optional)
conda remove -n Global_Dataset --all
```

---

## 📎 Notes

- `DTALite` is installable via pip and is used for traffic simulation and analysis.
- Ensure you have the latest version of Conda installed.
- Python version `3.12` is recommended for compatibility.