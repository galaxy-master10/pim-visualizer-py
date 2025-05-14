# requirements.md

# Very important issue is that this tool only works with sql and not other instances such as postgres and nosql

# Project Setup

This document explains how to get your development environment up and running for the ERD Explorer Streamlit application. It covers setting up the Python virtual environment, installing dependencies, and configuring the database connection string.

---

## 1. Activate the Python virtual environment

Before installing any packages, you must activate the project-specific virtual environment (`venv`).

**On Windows (PowerShell):**

1. Open a PowerShell prompt.
2. Navigate to the project root (`python-projects`):

   ```powershell
   cd C:\Users\<YourUser>\python-projects
   ```
3. Activate the venv:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

> After activation, your prompt should prefix with `(venv)`, indicating that you are now in the isolated environment.

**On macOS / Linux (bash/zsh):**

```bash
cd ~/python-projects
source venv/bin/activate
```
---
![Activate venv in PowerShell](image.png)

## 2. Install required dependencies

Once the venv is active, install all necessary Python libraries:

```bash
pip install streamlit==1.40.1 sqlalchemy==2.0.40 networkx==3.1 pyvis==0.3.2 pandas pyodbc
```

You can also install packages individually if preferred:

```bash
pip install streamlit sqlalchemy networkx pyvis
pip install pandas pyodbc
```

---

## 3. Verify installations

To confirm that the packages are correctly installed, run:

```bash
pip show streamlit sqlalchemy networkx pyvis pandas pyodbc
```

You should see information about each package (version, location, etc.) printed to the console.

---

## 4. Database connection string format

Your application uses a SQLAlchemy URI to connect to SQL Server via ODBC. The general pattern is:

```
mssql+pyodbc://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>?driver=<ODBC_DRIVER>&TrustServerCertificate=<yes|no>
```

* **USER**: your database user (e.g. `SA`)
* **PASSWORD**: URL-encoded password (e.g. `#` becomes `%23`)
* **HOST**: database host (e.g. `localhost`)
* **PORT**: TCP port for SQL Server (default `1433`)
* **DATABASE\_NAME**: your target schema/database (e.g. `Digit.Pim`)
* **ODBC\_DRIVER**: e.g. `ODBC+Driver+17+for+SQL+Server`
* **TrustServerCertificate**: `yes` or `no` depending on your TLS setup

**Example** (for your in-house `Digit.Pim` database):

```
mssql+pyodbc://SA:%23said8500@localhost:1433/Digit.Pim?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

> **Note:** Make sure to URL-encode any special characters in your password (e.g. `# → %23`).

---

## 5. Running the Streamlit app# requirements.md

# Project Setup

This document explains how to get your development environment up and running for the ERD Explorer Streamlit application. It covers setting up the Python virtual environment, installing dependencies, and configuring the database connection string.

---

## 1. Activate the Python virtual environment

Before installing any packages, you must activate the project-specific virtual environment (`venv`).

**On Windows (PowerShell):**

1. Open a PowerShell prompt.
2. Navigate to the project root (`python-projects`):

   ```powershell
   cd C:\Users\<YourUser>\python-projects
   ```
3. Activate the venv:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

> After activation, your prompt should prefix with `(venv)`, indicating that you are now in the isolated environment.

**On macOS / Linux (bash/zsh):**

```bash
cd ~/python-projects
source venv/bin/activate
```

---

## 2. Install required dependencies

Once the venv is active, install all necessary Python libraries:

```bash
pip install streamlit==1.40.1 sqlalchemy==2.0.40 networkx==3.1 pyvis==0.3.2 pandas pyodbc
```

You can also install packages individually if preferred:

```bash
pip install streamlit sqlalchemy networkx pyvis
pip install pandas pyodbc
```

---

## 3. Verify installations

To confirm that the packages are correctly installed, run:

```bash
pip show streamlit sqlalchemy networkx pyvis pandas pyodbc
```

You should see information about each package (version, location, etc.) printed to the console.

---

## 4. Database connection string format

Your application uses a SQLAlchemy URI to connect to SQL Server via ODBC. The general pattern is:

```
mssql+pyodbc://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>?driver=<ODBC_DRIVER>&TrustServerCertificate=<yes|no>
```

* **USER**: your database user (e.g. `SA`)
* **PASSWORD**: URL-encoded password (e.g. `#` becomes `%23`)
* **HOST**: database host (e.g. `localhost`)
* **PORT**: TCP port for SQL Server (default `1433`)
* **DATABASE\_NAME**: your target schema/database (e.g. `Digit.Pim`)
* **ODBC\_DRIVER**: e.g. `ODBC+Driver+17+for+SQL+Server`
* **TrustServerCertificate**: `yes` or `no` depending on your TLS setup

**Example** (for your in-house `Digit.Pim` database):

```
mssql+pyodbc://SA:%23said8500@localhost:1433/Digit.Pim?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

> **Note:** Make sure to URL-encode any special characters in your password (e.g. `# → %23`).

---

## 5. Running the Streamlit app

With venv activated and dependencies installed:

1. In your terminal (with `(venv)` prefix), run:

   ```bash
   python -m streamlit run app.py
   ```
2. A browser window will open at `http://localhost:8501`.
3. Paste your SQLAlchemy connection string in the input box and press Enter.
4. Wait for the “✅ Connection OK!” message, then explore your ERD diagram and table metadata.

---

## 6. Tips for in-house use

* **Version pinning** in `requirements.md` ensures reproducibility across team members.
* Encourage each developer to use the same ODBC driver version.
* Share any driver installation instructions (e.g. installing the Microsoft ODBC Driver 17 for SQL Server).
* You can customize `app.py` further, but keep this `requirements.md` updated with any added dependencies.


With venv activated and dependencies installed:

1. In your terminal (with `(venv)` prefix), run:

   ```bash
   python -m streamlit run app.py
   ```
2. A browser window will open at `http://localhost:8501`.
3. Paste your SQLAlchemy connection string in the input box and press Enter.
4. Wait for the “✅ Connection OK!” message, then explore your ERD diagram and table metadata.

---

## 6. Tips for in-house use

* **Version pinning** in `requirements.md` ensures reproducibility across team members.
* Encourage each developer to use the same ODBC driver version.
* Share any driver installation instructions (e.g. installing the Microsoft ODBC Driver 17 for SQL Server).
* You can customize `app.py` further, but keep this `requirements.md` updated with any added dependencies.
