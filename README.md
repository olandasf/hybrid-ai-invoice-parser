# 🍷 Excise Tax Calculator / Akcizų Skaičiuoklė

> AI-powered tool for automatic invoice data extraction and Lithuanian excise tax calculation

[English](#english) | [Lietuviškai](#lietuviškai)

---

## English

### Overview

A web-based automation tool for processing alcohol supplier invoices. The system automatically extracts product data from PDF/image invoices, classifies products by excise category, calculates taxes according to Lithuanian regulations, and exports results to Excel.

**Note:** UI is in Lithuanian as this tool is specifically designed for Lithuanian excise tax regulations.

### Features

- **Automatic data extraction** from EU supplier invoices (PDF, PNG, JPG, Word)
- **Multi-language support** - English, French, German, Italian, Spanish invoices
- **AI-powered OCR** using Google Document AI + DeepSeek LLM for semantic analysis
- **Automatic excise category classification** based on product type and ABV%
- **Transport cost allocation** - automatic or manual entry, distributed by volume/quantity
- **Tax calculation** according to 2026 Lithuanian excise rates
- **Web-based preview & editing** - review and correct data before saving
- **Excel export** with formulas and formatting
- **Cumulative Excel** - all invoices aggregated in one file
- **VMI declaration files** - automatic generation for tax authority
- **Banderole (tax stamp) assignment** - sequential numbering system

### Tech Stack

| Technology | Purpose |
|------------|---------|
| Python / Flask | Backend & web server |
| Google Document AI | Invoice OCR & structure extraction |
| DeepSeek LLM | Semantic analysis & data correction |
| HTML/CSS/JavaScript | Frontend interface |
| OpenPyXL | Excel file generation |

### How It Works

```
PDF/Image Upload → Document AI (OCR) → DeepSeek (Analysis) → 
→ Category Classification → Tax Calculation → Preview/Edit → Excel Export
```

### Excise Rates (2026)

| Category | Rate |
|----------|------|
| Ethyl alcohol (spirits) | 3130 EUR/HL pure alcohol |
| Beer | 12.74 EUR per 1% ABV/HL |
| Wine >8.5% ABV | 296 EUR/HL |
| Wine ≤8.5% ABV | 148 EUR/HL |
| Intermediate >15% ABV | 411 EUR/HL |
| Intermediate ≤15% ABV | 365 EUR/HL |

### Limitations

- Banderole assignment module is adapted for a specific batch/series (not fully universal)
- Primarily designed for EU supplier invoices (English, French, German, Italian, Spanish)
- Single-user application (no multi-user support)

### Transport Cost Allocation

The system supports automatic distribution of transport costs across invoice items:

- **Automatic extraction** - if transport costs are included in the invoice, they are extracted automatically
- **Manual entry** - before processing, you can manually enter transport cost amount
- **Smart allocation** - costs are distributed proportionally based on product volume and quantity
- **Cost tracking** - allocated transport costs are added to product unit price for accurate cost accounting

### Installation

```bash
# Clone repository
git clone https://github.com/olandasf/hybrid-ai-invoice-parser.git
cd hybrid-ai-invoice-parser

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit)
cp .env.example .env
```

### Running the Application

**Option 1: Direct command**
```bash
# Make sure virtual environment is activated first
python app.py
```

**Option 2: Using start scripts**
```bash
# Windows (PowerShell):
.\start.ps1

# Linux/macOS:
./start.sh
```

Application available at: **http://127.0.0.1:5000**

### Configuration

#### 1. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Document AI API**:
   - Navigation menu → APIs & Services → Enable APIs
   - Search for "Document AI API" and enable it

4. Create a Document AI Processor:
   - Go to [Document AI](https://console.cloud.google.com/ai/document-ai)
   - Click "Create Processor"
   - Select **Custom Extractor** (under "Generative AI" section)
   - Name it and create
   - Copy the **Processor ID** from the processor details page

5. Create Service Account credentials:
   - Go to IAM & Admin → Service Accounts
   - Create a new service account
   - Grant role: `Document AI API User`
   - Click on the service account → Keys → Add Key → Create new key → JSON
   - Download the JSON key file and save it securely

#### 2. DeepSeek API Setup

1. Go to [DeepSeek Platform](https://platform.deepseek.com/)
2. Create an account and get your API key

#### 3. Environment Variables

Create `.env` file with:
```env
# Google Document AI
GOOGLE_APPLICATION_CREDENTIALS=path/to/your-service-account-key.json
DOCAI_PROJECT_ID=your-google-cloud-project-id
DOCAI_PROCESSOR_ID=your-document-ai-processor-id
DOCAI_LOCATION=eu  # or 'us' depending on your processor location

# DeepSeek LLM
DEEPSEEK_API_KEY=your-deepseek-api-key
```

**Example:**
```env
GOOGLE_APPLICATION_CREDENTIALS=C:/keys/invoice-parser-credentials.json
DOCAI_PROJECT_ID=invoice-parser-project-460107
DOCAI_PROCESSOR_ID=abc123def456
DOCAI_LOCATION=eu
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## Lietuviškai

### Apžvalga

Web aplikacija, skirta automatizuoti alkoholinių gėrimų tiekėjų sąskaitų apdorojimą. Sistema automatiškai ištraukia produktų duomenis iš PDF/paveikslėlių, klasifikuoja produktus pagal akcizo kategoriją, skaičiuoja mokesčius pagal Lietuvos tarifus ir eksportuoja rezultatus į Excel.

### Funkcionalumas

- **Automatinis duomenų išgavimas** iš ES tiekėjų sąskaitų (PDF, PNG, JPG, Word)
- **Daugiakalbė sistema** - anglų, prancūzų, vokiečių, italų, ispanų kalbų sąskaitos
- **AI pagrįstas OCR** naudojant Google Document AI + DeepSeek LLM semantinei analizei
- **Automatinis akcizo kategorijos priskyrimas** pagal produkto tipą ir ABV%
- **Transporto išlaidų paskirstymas** - automatinis arba rankinis įvedimas, paskirstoma pagal tūrį/kiekį
- **Akcizo skaičiavimas** pagal 2026 m. Lietuvos tarifus
- **Web peržiūra ir redagavimas** - galimybė koreguoti duomenis prieš išsaugant
- **Excel eksportas** su formulėmis ir formatavimu
- **Kumuliacinis Excel** - visos sąskaitos vienoje suvestinėje
- **VMI deklaracijų failai** - automatinis generavimas
- **Banderolių priskyrimas** - nuosekli numeracija

### Technologijos

| Technologija | Paskirtis |
|--------------|-----------|
| Python / Flask | Backend ir web serveris |
| Google Document AI | Sąskaitų OCR ir struktūros išgavimas |
| DeepSeek LLM | Semantinė analizė ir duomenų korekcija |
| HTML/CSS/JavaScript | Vartotojo sąsaja |
| OpenPyXL | Excel failų generavimas |

### Veikimo schema

```
PDF/Paveikslėlis → Document AI (OCR) → DeepSeek (Analizė) → 
→ Kategorijos priskyrimas → Akcizo skaičiavimas → Peržiūra/Redagavimas → Excel
```

### Akcizų tarifai (2026 m.)

| Kategorija | Tarifas |
|------------|---------|
| Etilo alkoholis (spiritiniai) | 3130 EUR/HL gryno alkoholio |
| Alus | 12,74 EUR už 1% ABV/HL |
| Vynas >8,5% ABV | 296 EUR/HL |
| Vynas ≤8,5% ABV | 148 EUR/HL |
| Tarpinis produktas >15% ABV | 411 EUR/HL |
| Tarpinis produktas ≤15% ABV | 365 EUR/HL |

### Apribojimai

- Banderolių priskyrimo modulis adaptuotas konkrečiai partijai/serijai (ne pilnai universalus)
- Pritaikyta ES tiekėjų sąskaitoms (anglų, prancūzų, vokiečių, italų, ispanų kalbomis)
- Vieno vartotojo aplikacija

### Transporto išlaidų paskirstymas

Sistema palaiko automatinį transporto išlaidų paskirstymą tarp sąskaitos prekių:

- **Automatinis išgavimas** - jei transporto išlaidos įtrauktos į sąskaitą, jos išgaunamos automatiškai
- **Rankinis įvedimas** - prieš apdorojimą galima rankiniu būdu įvesti transporto išlaidų sumą
- **Išmanus paskirstymas** - išlaidos paskirstomos proporcingai pagal produkto tūrį ir kiekį
- **Savikainos apskaita** - paskirstytos transporto išlaidos pridedamos prie produkto vieneto kainos tiksliai savikainai

### Diegimas

```bash
# Klonuoti repozitoriją
git clone https://github.com/olandasf/hybrid-ai-invoice-parser.git
cd hybrid-ai-invoice-parser

# Sukurti virtualią aplinką
python -m venv venv

# Aktyvuoti virtualią aplinką
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Įdiegti priklausomybes
pip install -r requirements.txt

# Sukonfigūruoti aplinką
cp .env.example .env
```

### Aplikacijos paleidimas

**Būdas 1: Tiesiogiai per terminalą**
```bash
# Įsitikinkite, kad virtuali aplinka aktyvuota
python app.py
```

**Būdas 2: Naudojant paleidimo skriptus**
```bash
# Windows (PowerShell):
.\start.ps1

# Linux/macOS:
./start.sh
```

Aplikacija prieinama: **http://127.0.0.1:5000**

Aplikacija prieinama: **http://127.0.0.1:5000**

### Konfigūracija

#### 1. Google Cloud nustatymas

1. Eikite į [Google Cloud Console](https://console.cloud.google.com/)
2. Sukurkite naują projektą arba pasirinkite esamą
3. Įjunkite **Document AI API**:
   - Navigacija → APIs & Services → Enable APIs
   - Ieškokite "Document AI API" ir įjunkite

4. Sukurkite Document AI procesorių:
   - Eikite į [Document AI](https://console.cloud.google.com/ai/document-ai)
   - Spauskite "Create Processor"
   - Pasirinkite **Custom Extractor** (skiltyje "Generative AI")
   - Pavadinkite ir sukurkite
   - Nukopijuokite **Processor ID** iš procesoriaus detalių puslapio

5. Sukurkite Service Account kredencialus:
   - IAM & Admin → Service Accounts
   - Sukurkite naują service account
   - Suteikite rolę: `Document AI API User`
   - Spauskite ant service account → Keys → Add Key → Create new key → JSON
   - Atsisiųskite JSON raktų failą ir saugokite jį saugiai

#### 2. DeepSeek API nustatymas

1. Eikite į [DeepSeek Platform](https://platform.deepseek.com/)
2. Sukurkite paskyrą ir gaukite API raktą

#### 3. Aplinkos kintamieji

Sukurkite `.env` failą:
```env
# Google Document AI
GOOGLE_APPLICATION_CREDENTIALS=kelias/iki/jusu-service-account-raktas.json
DOCAI_PROJECT_ID=jusu-google-cloud-projekto-id
DOCAI_PROCESSOR_ID=jusu-document-ai-procesoriaus-id
DOCAI_LOCATION=eu  # arba 'us' priklausomai nuo procesoriaus lokacijos

# DeepSeek LLM
DEEPSEEK_API_KEY=jusu-deepseek-api-raktas
```

---

## 📁 Project Structure / Projekto struktūra

```
├── app.py                 # Flask web server
├── ai_invoice.py          # AI invoice processing
├── akcizai.py             # Excise tax rates & calculation
├── banderoles.py          # Tax stamp management
├── category.py            # Alcohol classification
├── generate_excel.py      # Excel export
├── generate_vmi.py        # VMI declaration files
├── cumulative_excel.py    # Cumulative Excel management
├── simple_cache.py        # Caching system
├── utils.py               # Helper functions
├── templates/             # HTML templates
├── static/                # CSS/JS files
└── tests/                 # Unit tests
```

---

## 📄 License / Licencija

MIT License

© 2025-2026 Rolandas Fokas
