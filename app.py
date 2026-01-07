import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, Response, send_file
from werkzeug.utils import secure_filename
import json
import time

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

from ai_invoice import extract_invoice_data
from akcizai import enrich_products_with_excise, CATEGORY_LABELS
from generate_excel import generate_excel_file, get_column_map_for_excel
from generate_csv import generate_csv_string
from utils import clean_and_convert_to_float as try_convert_to_float, log_function_call
from simple_cache import pdf_cache
from banderoles import enrich_products_with_banderoles, get_banderole_statistics
from generate_vmi import generate_vmi_files_for_products
from cumulative_excel import cumulative_excel_manager
from datetime import date, datetime

app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')))
print(f"Flask template folder set to: {app.template_folder}")
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config.update(UPLOAD_FOLDER='uploads', OUTPUT_FOLDER='output')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

def allowed_file(filename):
    """Tikrina, ar įkelto failo plėtinys yra leistinas."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# try_convert_to_float funkcija perkelta į utils.py

def apply_discount(products: list, discount: float, subtotal: float) -> list:
    """Taiko bendrą nuolaidą produktams proporcingai pagal jų vertę."""
    if not products:
        return products
    
    # Jei nuolaidos nėra, priskiriam originalias kainas ir grąžinam
    if not discount or discount <= 0:
        for p in products:
            p['unit_price_original'] = p.get('unit_price')
            p['unit_price_with_discount'] = p.get('unit_price')
            p['amount_with_discount'] = p.get('amount')
            p['discount_percentage'] = 0.0
        return products
    
    # Apskaičiuojam tarpinę sumą, jei ji nebuvo pateikta
    if not subtotal or subtotal <= 0:
        subtotal = sum(try_convert_to_float(p.get('amount')) or 0 for p in products)
    
    discount_percentage = (discount / subtotal) * 100 if subtotal > 0 else 0
    
    processed = []
    for p_dict in products:
        p = p_dict.copy()
        p['unit_price_original'] = p.get('unit_price')
        
        original_amount = try_convert_to_float(p.get('amount')) or 0
        quantity = try_convert_to_float(p.get('quantity')) or 0
        
        if original_amount > 0 and quantity > 0 and subtotal > 0:
            proportion = original_amount / subtotal
            item_discount = discount * proportion
            new_amount = original_amount - item_discount
            new_unit_price = new_amount / quantity if quantity > 0 else 0
            
            p['unit_price_with_discount'] = new_unit_price
            p['amount_with_discount'] = new_amount
            p['discount_percentage'] = discount_percentage
        else:
            p['unit_price_with_discount'] = p.get('unit_price')
            p['amount_with_discount'] = p.get('amount')
            p['discount_percentage'] = discount_percentage
        
        processed.append(p)
    
    return processed

def format_products_for_display(products: list) -> list:
    """Formatuoja skaitines produktų reikšmes kaip tekstą su nustatytu tikslumu, skirtą atvaizdavimui."""
    formatted_products = []
    for p in products:
        p_copy = p.copy()
        for key, value in p_copy.items():
            if isinstance(value, (int, float)):
                if key in ['excise_per_unit', 'transport_per_unit']:
                    p_copy[key] = f"{value:.4f}"
                elif key == 'volume':
                    p_copy[key] = f"{value:.3f}"
                elif key == 'quantity':
                    p_copy[key] = f"{value:.0f}"
                else:
                    p_copy[key] = f"{value:.2f}"
        formatted_products.append(p_copy)
    return formatted_products

@app.route('/', methods=['GET', 'POST'])
def main_route():
    """Pagrindinis maršrutas, apdorojantis failo įkėlimą ir pirminį duomenų ištraukimą."""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            flash('Būtina įkelti failą (PDF, PNG, JPG arba Word).', 'error')
            return redirect(request.url)
        
        # Sukurti unikalų failo vardą su timestamp
        if not file.filename:
            flash('Failas neturi pavadinimo.', 'error')
            return redirect(request.url)
            
        original_filename = secure_filename(file.filename)
        base, ext = os.path.splitext(original_filename)
        timestamp = int(time.time())
        filename = f"{base}_{timestamp}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            logging.info(f"Failas sėkmingai išsaugotas: {filepath}")
        except Exception as e:
            logging.error(f"Nepavyko išsaugoti failo: {e}")
            flash('Klaida išsaugojant failą. Bandykite dar kartą.', 'error')
            return redirect(request.url)
        
        # Gauti rankinį transporto įvedimą
        manual_transport = try_convert_to_float(request.form.get('transport_total', 0.0)) or 0.0
        
        logging.info("Pradedamas sąskaitos apdorojimas: %s", filepath)
        logging.info("Rankinis transporto įvedimas: %.2f€", manual_transport)
        
        # Duomenų ištraukimas su rankiniu transportu
        data = extract_invoice_data(filepath, manual_transport)
        
        # Patikrinti ar yra klaidų
        if 'error' in data:
            # Išvalyti laikinį failą klaidos atveju
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logging.info(f"Laikinas failas pašalintas po klaidos: {filepath}")
            except Exception as e:
                logging.warning(f"Nepavyko pašalinti laikino failo po klaidos: {e}")
            
            flash(f'Klaida apdorojant sąskaitą: {data["error"]}', 'error')
            return redirect(url_for('main_route'))
        
        products = data.get('products', [])
        summary = data.get('summary', {})
        final_transport = summary.get('transport_amount', 0.0)
        transport_source = summary.get('transport_source', 'none')

        if not products:
            # Išvalyti laikinį failą jei nėra produktų
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logging.info(f"Laikinas failas pašalintas (nėra produktų): {filepath}")
            except Exception as e:
                logging.warning(f"Nepavyko pašalinti laikino failo (nėra produktų): {e}")
            
            # Jei nėra produktų, bet yra transporto informacija, vis tiek rodome pranešimą
            if final_transport > 0:
                flash(f'Nepavyko ištraukti produktų duomenų, bet rastas transportas: {final_transport:.2f} EUR. Patikrinkite PDF kokybę.', 'warning')
            else:
                flash('Nepavyko ištraukti duomenų iš sąskaitos naudojant AI arba sąskaita tuščia. Duomenys gali būti netikslūs.', 'error')
            return redirect(url_for('main_route'))
        
        # TRANSPORTO INFORMACIJOS APDOROJIMAS
        transport_warnings = []
        
        # Validuojame transporto sumą
        if final_transport > 10000:
            transport_warnings.append(f"Transporto suma ({final_transport:.2f} EUR) yra labai didelė")
        
        # Nustatome pranešimus pagal transporto šaltinį
        if transport_source == 'manual':
            logging.info("Naudojamas rankinis transportas: %.2f€", final_transport)
            flash(f'🔵 Naudojamas įvestas transportas: {final_transport:.2f} EUR', 'info')
        elif transport_source == 'automatic':
            logging.info("Naudojamas automatiškai rastas transportas: %.2f€", final_transport)
            flash(f'🟢 Automatiškai rastas transportas: {final_transport:.2f} EUR', 'success')
        else:
            logging.info("Transportas nerastas")
            flash('🟠 Transportas nerastas sąskaitoje. Jei reikia, galite įvesti rankiniu būdu.', 'info')
        
        # Transporto informacijos objektas UI
        transport_info = {
            'amount': final_transport,
            'source': transport_source,
            'auto_detected': final_transport if transport_source == 'automatic' else 0.0,
            'manual_entered': final_transport if transport_source == 'manual' else 0.0,
            'warnings': transport_warnings
        }
        
        # Pridėti įspėjimus kaip flash pranešimus
        for warning in transport_warnings:
            flash(warning, 'warning')
        
        # Saugoti session'e galutinę transporto sumą
        session['transport_total'] = final_transport
        session['transport_info'] = transport_info
        session['invoice_summary'] = summary  # Išsaugome visą suvestinę
        
        # Nuolaidos ir tarpinės sumos nustatymas
        discount = abs(try_convert_to_float(summary.get('discount_amount', 0.0)) or 0.0)
        subtotal = sum(try_convert_to_float(p.get('amount')) or 0 for p in products)
        
        logging.info("Nustatyta nuolaida: %.2f€, Subtotal: %.2f€", discount, subtotal)
        
        products_with_discount = apply_discount(products, discount, subtotal)
        
        # Validuoti produktų duomenis prieš praturtinimą
        validated_products = []
        for product in products_with_discount:
            validated_product = {
                'name': str(product.get('name', '')),
                'volume': try_convert_to_float(product.get('volume')) or 0.0,
                'abv': try_convert_to_float(product.get('abv')) or 0.0,
                'quantity': try_convert_to_float(product.get('quantity')) or 0.0,
                'unit_price': try_convert_to_float(product.get('unit_price')) or 0.0,
                'amount': try_convert_to_float(product.get('amount')) or 0.0,
                'unit_price_with_discount': try_convert_to_float(product.get('unit_price_with_discount')) or try_convert_to_float(product.get('unit_price')) or 0.0,
                'amount_with_discount': try_convert_to_float(product.get('amount_with_discount')) or try_convert_to_float(product.get('amount')) or 0.0,
                'discount_percentage': try_convert_to_float(product.get('discount_percentage')) or 0.0,
                'excise_category_key': product.get('excise_category_key', 'non_alcohol')
            }
            validated_products.append(validated_product)
        
        # Praturtinti produktus akcizo duomenimis
        enriched_products = enrich_products_with_excise(validated_products, final_transport)
        
        # Priskirti banderoles
        logging.info(f"Prieš banderolių priskyrimą: {len(enriched_products)} produktų")
        products_with_banderoles = enrich_products_with_banderoles(enriched_products)
        logging.info(f"Po banderolių priskyrimo: {len(products_with_banderoles)} produktų")
        
        # Patikrinti ar produktai turi banderolių informaciją
        banderole_count = sum(1 for p in products_with_banderoles if 'banderole_type' in p)
        logging.info(f"Produktų su banderolėmis: {banderole_count}/{len(products_with_banderoles)}")
        
        # Saugoti session'e tik būtinus laukus VMI generavimui (sumažinti session dydį)
        vmi_products = []
        for product in products_with_banderoles:
            # Tik būtini laukai VMI generavimui
            vmi_product = {
                'name': product.get('name'),
                'quantity': product.get('quantity'),
                'volume': product.get('volume'),
                'abv': product.get('abv'),
                'banderole_type': product.get('banderole_type'),
                'banderole_code': product.get('banderole_code'),
                'banderole_start': product.get('banderole_start'),
                'banderole_end': product.get('banderole_end'),
                'banderole_count': product.get('banderole_count'),
                'tariff_group': product.get('tariff_group')
            }
            # Pašalinti None reikšmes
            vmi_product = {k: v for k, v in vmi_product.items() if v is not None}
            vmi_products.append(vmi_product)
        
        # Išvalyti Undefined objektus prieš saugojimą į session
        clean_vmi_products = []
        for product in vmi_products:
            clean_product = {}
            for key, value in product.items():
                # Patikrinti ar vertė nėra Undefined
                if (value is not None and 
                    not hasattr(value, '__class__') or 
                    'Undefined' not in str(type(value))):
                    try:
                        # Bandyti konvertuoti į JSON - jei Undefined, kels klaidą
                        import json
                        json.dumps(value)
                        clean_product[key] = value
                    except (TypeError, ValueError):
                        # Jei negalima serializuoti - praleisti
                        continue
            clean_vmi_products.append(clean_product)
        
        # Išsaugoti pilnus duomenis �į failą (session per didelis)
        import json
        import tempfile
        
        # Sukurti laikinų failų katalogą jei neegzistuoja
        temp_dir = os.path.join(os.getcwd(), 'temp_data')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Sukurti session ID jei neegzistuoja
        if 'session_id' not in session:
            import uuid
            session['session_id'] = str(uuid.uuid4())[:8]
        
        # Išsaugoti pilnus duomenis į failą
        full_data_file = os.path.join(temp_dir, f'full_products_{session.get("session_id", "default")}.json')
        try:
            with open(full_data_file, 'w', encoding='utf-8') as f:
                json.dump(products_with_banderoles, f, ensure_ascii=False, default=str)
            session['full_products_file'] = full_data_file
            logging.info(f"Pilni duomenys išsaugoti į failą: {full_data_file}")
        except Exception as e:
            logging.error(f"Klaida saugant pilnus duomenis: {e}")
        
        # Išsaugoti sumažintus duomenis VMI'ui (session'e)
        session['processed_products'] = clean_vmi_products
        logging.info(f"Išsaugota {len(clean_vmi_products)} išvalytų produktų su banderolėmis session'e")
        
        display_products = format_products_for_display(products_with_banderoles)
        
        column_keys_for_js = [key for key, _ in get_column_map_for_excel()]
        
        # Išvalyti laikinį failą po sėkmingo apdorojimo
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"Laikinas failas pašalintas: {filepath}")
        except Exception as e:
            logging.warning(f"Nepavyko pašalinti laikino failo: {e}")
        
        # Gauti banderolių statistikas
        banderole_stats = get_banderole_statistics()
        
        # Nustatyti default datas VMI failams
        today = date.today()
        default_period_start = today
        default_period_end = today
        
        return render_template('preview.html', 
                             products=display_products, 
                             transport_total=final_transport,
                             transport_info=transport_info,
                             discount_total=discount, 
                             category_labels=CATEGORY_LABELS,
                             column_headers_display=get_column_map_for_excel(),
                             column_keys_for_js=column_keys_for_js,
                             banderole_stats=banderole_stats,
                             default_period_start=default_period_start.strftime('%Y-%m-%d'),
                             default_period_end=default_period_end.strftime('%Y-%m-%d'),
                             current_year=2025)
    
    return render_template('index.html')

@app.route('/recalculate_item_data', methods=['POST'])
def recalculate_item_data():
    """Perskaičiuoja vienos prekės eilutės duomenis pagal vartotojo įvestį."""
    try:
        data = request.get_json()
        product_index = data.get('product_index')
        transport_total = data.get('transport_total', 0.0)
        all_products = data.get('all_products', [])
        
        if product_index is None or not all_products:
            return jsonify({'error': 'Trūksta duomenų (indekso arba produktų sąrašo)'}), 400

        for p in all_products:
            for key, value in p.items():
                if key in ['volume', 'abv', 'quantity', 'unit_price', 'amount', 'discount_percentage', 'unit_price_with_discount']:
                    p[key] = try_convert_to_float(value)
        
        enriched_list = enrich_products_with_excise(all_products, transport_total)
        
        # Praturtinti banderolių duomenimis visą sąrašą
        enriched_with_banderoles = enrich_products_with_banderoles(enriched_list)
        
        # SVARBU: Atnaujinti sesijos failą su VISAIS produktais (įskaitant vartotojo pakeitimus)
        full_products_file = session.get('full_products_file')
        if full_products_file and os.path.exists(full_products_file):
            try:
                with open(full_products_file, 'w', encoding='utf-8') as f:
                    json.dump(enriched_with_banderoles, f, ensure_ascii=False, default=str)
                logging.info(f"Sesijos failas atnaujintas po eilutės perskaičiavimo: {full_products_file}")
            except Exception as e:
                logging.error(f"Nepavyko atnaujinti sesijos failo: {e}")
        
        if 0 <= product_index < len(enriched_with_banderoles):
            return jsonify(enriched_with_banderoles[product_index])
        else:
            return jsonify({'error': 'Gautas neteisingas produkto indeksas'}), 400
            
    except Exception as e:
        logging.error(f"Klaida perskaičiuojant prekės duomenis: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/recalculate_all_products', methods=['POST'])
def recalculate_all_products():
    """Perskaičiuoja visos lentelės duomenis ir atnaujina sesijos failą."""
    try:
        data = request.get_json()
        products = data.get('products', [])
        transport_total = data.get('transport_total', 0.0)
        
        # 1. Konvertuoti skaitines reikšmes
        for product in products:
            for key, value in product.items():
                if key in ['volume', 'abv', 'quantity', 'unit_price', 'amount', 'discount_percentage', 'unit_price_with_discount', 'excise_per_unit', 'transport_per_unit']:
                    product[key] = try_convert_to_float(value)
        
        # 2. Praturtinti akcizo duomenimis
        enriched_excise = enrich_products_with_excise(products, transport_total)
        
        # 3. Praturtinti banderolių duomenimis
        enriched_banderoles = enrich_products_with_banderoles(enriched_excise)
        
        # 4. Atnaujinti sesijos failą
        full_products_file = session.get('full_products_file')
        if full_products_file and os.path.exists(full_products_file):
            try:
                with open(full_products_file, 'w', encoding='utf-8') as f:
                    json.dump(enriched_banderoles, f, ensure_ascii=False, default=str)
                logging.info(f"Sėkmingai atnaujintas sesijos failas: {full_products_file}")
            except Exception as e:
                logging.error(f"Nepavyko atnaujinti sesijos failo: {e}")
        else:
            logging.warning("Nepavyko rasti sesijos failo atnaujinimui.")

        # 5. Grąžinti pilnai praturtintus duomenis naršyklei
        return jsonify(enriched_banderoles)
        
    except Exception as e:
        logging.error(f"Klaida perskaičiuojant visų prekių duomenis: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/generate_excel', methods=['POST'])
def generate_excel_route():
    """Generuoja ir pateikia Excel failą atsisiuntimui."""
    try:
        # Naudoti pilnus, jau apdorotus duomenis iš laikino failo
        full_products_file = session.get('full_products_file')
        if not full_products_file or not os.path.exists(full_products_file):
            flash("Nėra apdorotų produktų duomenų. Pirmiausia įkelkite sąskaitą.", "error")
            return redirect(url_for('main_route'))

        with open(full_products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)

        # Duomenys jau yra praturtinti, todėl nebekviečiame enrich_products_with_excise
        
        # Generuoti Excel failą
        filepath = generate_excel_file(products)
        
        # Grąžinti failą
        return send_from_directory(app.config['OUTPUT_FOLDER'], os.path.basename(filepath), as_attachment=True)
        
    except Exception as e:
        logging.error(f"Excel generavimo klaida: {e}", exc_info=True)
        flash(f"Klaida generuojant Excel failą: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/generate_cumulative_excel', methods=['POST'])
def generate_cumulative_excel_route():
    """Prideda sąskaitą į kumuliacinį Excel failą."""
    try:
        # Pakeista: Naudoti pilnus, jau apdorotus duomenis iš laikino failo, o ne iš formos
        full_products_file = session.get('full_products_file')
        if not full_products_file or not os.path.exists(full_products_file):
            flash("Nėra apdorotų produktų duomenų. Pirmiausia įkelkite sąskaitą.", "error")
            return redirect(url_for('main_route'))

        with open(full_products_file, 'r', encoding='utf-8') as f:
            products_with_banderoles = json.load(f)

        # Naudojame session'e saugomą transporto sumą ir suvestinę
        transport_total = session.get('transport_total', 0.0)
        summary = session.get('invoice_summary', {})
        
        # Pridėti į kumuliacinį failą
        file_path, sheet_name = cumulative_excel_manager.add_invoice_to_cumulative_file(
            products_with_banderoles, transport_total, summary
        )
        
        # Informuoti vartotoją
        flash(f"Sąskaita sėkmingai pridėta į kumuliacinį Excel failą! Lapas: '{sheet_name}'", "success")
        
        # Grįžti į preview puslapį
        return redirect(url_for('show_preview'))
        
    except Exception as e:
        logging.error(f"Kumuliacinio Excel generavimo klaida: {e}", exc_info=True)
        flash(f"Klaida pridedant į kumuliacinį Excel failą: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/generate_csv', methods=['POST'])
def generate_csv_route():
    """Generuoja ir pateikia CSV failą atsisiuntimui."""
    try:
        products_json = request.form.get('products_csv')
        if not products_json:
            flash("Negauta duomenų CSV generavimui.", "error")
            return redirect(url_for('main_route'))
        
        products = json.loads(products_json)
        
        # Naudojame session'e saugomą transporto sumą
        transport_total = session.get('transport_total', 0.0)
        enriched_products = enrich_products_with_excise(products, transport_total)
        csv_string = generate_csv_string(enriched_products)
        
        return Response(
            csv_string,
            mimetype="text/csv; charset=utf-8-sig",
            headers={"Content-disposition": "attachment; filename=akcizo_apskaita.csv"}
        )
    except Exception as e:
        logging.error(f"CSV generavimo klaida: {e}", exc_info=True)
        flash(f"Klaida generuojant CSV failą: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/generate_vmi', methods=['POST'])
def generate_vmi_route():
    """Generuoja VMI banderolių apskaitos failus."""
    try:
        # Gauti duomenis iš formos
        period_start_str = request.form.get('period_start')
        period_end_str = request.form.get('period_end')
        banderole_type = request.form.get('banderole_type', 'both')  # 'BAC', 'AAH', arba 'both'
        
        if not period_start_str or not period_end_str:
            flash("Būtina nurodyti atskaitinio laikotarpio datas.", "error")
            return redirect(url_for('main_route'))
        
        # Konvertuoti datas
        try:
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Neteisingas datų formatas.", "error")
            return redirect(url_for('main_route'))
        
        # Gauti produktus iš session (prioritetas)
        products = session.get('processed_products', [])
        logging.info(f"Gauti produktai iš session: {len(products)}")
        
        # Jei session tuščias, bandyti iš formos
        if not products:
            products_json = request.form.get('products_data')
            if products_json:
                try:
                    import json
                    products = json.loads(products_json)
                    logging.info(f"Gauti produktai iš formos: {len(products)}")
                    
                    # Jei produktai neturi banderolių informacijos, priskirti ją
                    if products and 'banderole_type' not in products[0]:
                        logging.info("Produktai neturi banderolių informacijos, priskiriu...")
                        products = enrich_products_with_banderoles(products)
                        
                except Exception as e:
                    logging.error(f"Klaida parsint produktus iš formos: {e}")
        
        # Pirmiausia bandykime gauti pilnus duomenis iš failo, jei jis egzistuoja
        full_products_file = session.get('full_products_file')
        if full_products_file and os.path.exists(full_products_file):
            try:
                with open(full_products_file, 'r', encoding='utf-8') as f:
                    full_products = json.load(f)
                logging.info(f"Įkelti pilni produktų duomenys iš failo: {len(full_products)}")
                # Patikriname, ar pilni duomenys turi daugiau informacijos nei session duomenys
                if full_products and (not products or len(full_products) == len(products)):
                    products = full_products
                    logging.info("Naudoti pilni duomenys iš failo")
            except Exception as e:
                logging.error(f"Klaida skaitant pilnus duomenis iš failo: {e}")
        
        if not products:
            flash("Nėra apdorotų produktų duomenų. Pirmiausia įkelkite sąskaitą.", "error")
            return redirect(url_for('main_route'))
        
        # Filtruoti produktus pagal banderolės tipą jei reikia
        if banderole_type == 'BAC':
            products = [p for p in products if p.get('banderole_type') == 'BAC']
        elif banderole_type == 'AAH':
            products = [p for p in products if p.get('banderole_type') == 'AAH']
        # Jei pasirinktas 'both', naudoti visus alkoholinius produktus su banderolėmis
        elif banderole_type == 'both':
            products = [p for p in products if p.get('banderole_type') in ['BAC', 'AAH']]
        
        if not products:
            flash(f"Nėra produktų su {banderole_type} banderolėmis.", "warning")
            return redirect(url_for('main_route'))
        
        # Debug: patikrinti produktų duomenis prieš VMI generavimą
            logging.info("Produktai prieš VMI generavimą: {len(products)}")
            if not products:
                logging.error("PRODUKTŲ SĄRAŠAS TUŠČIAS! VMI generavimas neįmanomas.")
                flash("Nėra produktų duomenų VMI generavimui. Patikrinkite ar sąskaita buvo sėkmingai apdorota.", "error")
                return redirect(url_for('main_route'))
        
        for i, product in enumerate(products[:3]):  # Rodyti tik pirmus 3
            logging.info(f"Produktas {i}: {product.get('name')} - {product.get('banderole_type')} - {product.get('banderole_start')}-{product.get('banderole_end')}")
            
        # Patikrinti ar produktai turi banderolių informaciją
        products_without_banderoles = [p for p in products if not p.get('banderole_type')]
        if products_without_banderoles:
            logging.warning(f"{len(products_without_banderoles)} produktai neturi banderolių informacijos")
            # Pabandyti priskirti banderoles dar kartą
            try:
                products = enrich_products_with_banderoles(products)
                logging.info("Banderolės priskirtos sėkmingai")
            except Exception as e:
                logging.error(f"Klaida priskiriant banderoles: {e}")
                flash(f"Klaida priskiriant banderoles: {e}", "error")
                return redirect(url_for('main_route'))
        
        # Pridėti duomenis į esamus VMI failus
        try:
            from generate_vmi import append_to_existing_vmi_files
            logging.info(f"Prieš kviečiant append_to_existing_vmi_files: {len(products)} produktai")
            
            # Debug: parodyti pirmus produktus
            for i, product in enumerate(products[:3]):
                logging.info(f"  Produktas {i+1}: {product.get('name', 'N/A')} - banderolės tipas: {product.get('banderole_type', 'N/A')}")
            
            success_bac, success_aah = append_to_existing_vmi_files(
                products, period_start, period_end
            )
            logging.info(f"VMI duomenų pridėjimo rezultatas: BAC={success_bac}, AAH={success_aah}")
            logging.info(f"Rezultatų tipai: BAC={type(success_bac)}, AAH={type(success_aah)}")
        except Exception as e:
            logging.error(f"VMI duomenų pridėjimo klaida: {e}", exc_info=True)
            flash(f"Klaida pridedant duomenis į VMI failus: {e}", "error")
            return redirect(url_for('main_route'))
        
        # Patikrinti rezultatus ir parodyti pranešimą
        files_updated = []
        # Tikriname kiekvieną reikšmę atskirai, kadangi jos gali būti True, False arba None
        if success_bac is True:
            files_updated.append("BAC.csv (putojantys vynai)")
        if success_aah is True:
            files_updated.append("AAH.csv (alkoholis)")
        
        logging.info(f"Failų atnaujinimo rezultatai: {files_updated}")
        
        # Tiksliau tikriname rezultatus
        if files_updated:
            flash(f"VMI failai sėkmingai atnaujinti: {', '.join(files_updated)}. Duomenys pridėti į esamus failus su tęstine numeracija.", "success")
        elif success_bac is None or success_aah is None:
            # Kritinė klaida - funkcija grąžino None
            flash("Klaida atnaujinant VMI failus. Patikrinkite žurnalus dėl išsamesnės informacijos.", "error")
        elif success_bac is False and success_aah is False:
            # Abi funkcijos grąžino False - patikriname priežastis
            alkoholiniai_produktai = [p for p in products if p.get('banderole_type') in ['BAC', 'AAH']]
            logging.info(f"Alkoholinių produktų skaičius: {len(alkoholiniai_produktai)}")
            if not alkoholiniai_produktai:
                flash("Nebuvo alkoholinių produktų su banderolėmis. VMI failai neatnaujinti, nes sąskaitoje nėra produktų, kuriems reikia banderolių.", "warning")
            else:
                flash("Nepavyko atnaujinti VMI failų. Patikrinkite žurnalus dėl išsamesnės informacijos.", "error")
        else:
            # Patikriname ar buvo alkoholinių produktų
            alkoholiniai_produktai = [p for p in products if p.get('banderole_type') in ['BAC', 'AAH']]
            if alkoholiniai_produktai:
                # Jei buvo alkoholinių produktų, bet files_updated tuščias, tai reiškia, kad success_bac ir/ar success_aah yra True
                # bet mes jų nepridėjome į files_updated sąrašą
                messages = []
                if success_bac is True:
                    messages.append("BAC.csv (putojantys vynai)")
                if success_aah is True:
                    messages.append("AAH.csv (alkoholis)")
                
                if messages:
                    flash(f"VMI failai sėkmingai atnaujinti: {', '.join(messages)}. Duomenys pridėti į esamus failus su tęstine numeracija.", "success")
                else:
                    # Šis atvejis įvyksta kai success_bac arba success_aah yra True, bet mes jų nepridėjome į messages
                    # Tai reiškia, kad turime patikrinti kiekvieną reikšmę atskirai
                    if success_bac is True or success_aah is True:
                        updated_files = []
                        if success_bac is True:
                            updated_files.append("BAC.csv (putojantys vynai)")
                        if success_aah is True:
                            updated_files.append("AAH.csv (alkoholis)")
                        flash(f"VMI failai sėkmingai atnaujinti: {', '.join(updated_files)}. Duomenys pridėti į esamus failus su tęstine numeracija.", "success")
                    else:
                        flash("VMI failai sėkmingai atnaujinti. Duomenys pridėti į esamus failus su tęstine numeracija.", "success")
            else:
                flash("VMI failai neatnaujinti. Patikrinkite ar pasirinkote produktus su banderolėmis.", "warning")

        # Grįžti į preview puslapį - tiesiogiai be papildomo apdorojimo
        return redirect(url_for('show_preview'))
        
    except Exception as e:
        logging.error(f"VMI failų generavimo klaida: {e}", exc_info=True)
        flash(f"Klaida generuojant VMI failus: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/preview')
def show_preview():
    """Rodo preview puslapį su session duomenimis."""
    try:
        # Išvalyti session nuo Undefined objektų
        session.permanent = True
        
        # Sukurti session ID jei neegzistuoja
        if 'session_id' not in session:
            import uuid
            session['session_id'] = str(uuid.uuid4())[:8]
        
        # Gauti pilnus duomenis iš failo arba session
        raw_products = []
        full_products_file = session.get('full_products_file')
        
        if full_products_file and os.path.exists(full_products_file):
            try:
                with open(full_products_file, 'r', encoding='utf-8') as f:
                    raw_products = json.load(f)
                logging.info(f"Įkelta {len(raw_products)} produktų iš failo: {full_products_file}")
            except Exception as e:
                logging.error(f"Klaida skaitant pilnus duomenis iš failo: {e}")
                raw_products = session.get('processed_products', [])
        else:
            # Fallback į session duomenis
            raw_products = session.get('processed_products', [])
            
        raw_transport = session.get('transport_total', 0.0)
        
        if not raw_products:
            flash("Nėra apdorotų duomenų. Pirmiausia įkelkite sąskaitą.", "warning")
            return redirect(url_for('main_route'))
        
        # Tiesiog naudoti duomenis iš session be papildomo apdorojimo
        clean_products = raw_products
        
        # Formatuoti skaičius
        display_products = []
        for product in clean_products:
            formatted_product = product.copy()
            
            # Formatuoti pinigus
            for key in ['unit_price', 'amount', 'excise_per_unit', 'excise_total', 
                       'transport_per_unit', 'transport_total', 'cost_wo_vat', 'cost_w_vat']:
                if key in formatted_product:
                    try:
                        formatted_product[key] = f"{float(formatted_product[key]):.2f}"
                    except:
                        formatted_product[key] = "0.00"
            
            # Formatuoti tūrį
            if 'volume' in formatted_product:
                try:
                    formatted_product['volume'] = f"{float(formatted_product['volume']):.3f}"
                except:
                    formatted_product['volume'] = "0.000"
            
            # Formatuoti kiekį
            if 'quantity' in formatted_product:
                try:
                    formatted_product['quantity'] = f"{float(formatted_product['quantity']):.0f}"
                except:
                    formatted_product['quantity'] = "0"
            
            display_products.append(formatted_product)
        
        # Saugus transportas
        safe_transport = 0.0
        try:
            safe_transport = float(raw_transport)
        except:
            safe_transport = 0.0
        
        # VMI datos
        from datetime import date
        today = date.today()
        
        # Importuoti reikalingus kintamuosius
        from akcizai import CATEGORY_LABELS
        from generate_excel import get_column_map_for_excel
        
        return render_template('preview.html',
                             products=display_products,
                             transport_total=safe_transport,
                             default_period_start=today.replace(day=1).strftime('%Y-%m-%d'),
                             default_period_end=today.strftime('%Y-%m-%d'),
                             category_labels=CATEGORY_LABELS,
                             column_headers_display=get_column_map_for_excel(),
                             column_keys_for_js=[])
                             
    except Exception as e:
        logging.error(f"Klaida rodant preview: {e}", exc_info=True)
        # Išvalyti session ir nukreipti į pradžią
        session.clear()
        flash("Klaida rodant duomenis. Session išvalytas.", "error")
        return redirect(url_for('main_route'))

@app.route('/banderole_stats')
def banderole_stats_route():
    """Grąžina banderolių statistikas JSON formatu."""
    try:
        stats = get_banderole_statistics()
        return jsonify(stats)
    except Exception as e:
        logging.error("Klaida gaunant banderolių statistiką: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/cumulative_excel_stats')
def cumulative_excel_stats_route():
    """Grąžina kumuliacinių Excel failų statistikas JSON formatu."""
    try:
        stats = cumulative_excel_manager.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logging.error("Klaida gaunant kumuliacinių Excel statistiką: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/download_cumulative_excel')
def download_cumulative_excel_route():
    """Atsisiųsti dabartinių metų kumuliacinį Excel failą."""
    try:
        file_path = cumulative_excel_manager.get_cumulative_file_path()
        
        if not file_path.exists():
            flash("Kumuliacinio Excel failo nėra. Pirmiausia pridėkite sąskaitą.", "error")
            return redirect(url_for('main_route'))
        
        return send_file(str(file_path), as_attachment=True)
        
    except Exception as e:
        logging.error(f"Klaida atsisiunčiant kumuliacinį Excel failą: {e}")
        flash(f"Klaida atsisiunčiant failą: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/debug/session')
def debug_session():
    """Debug route session duomenų tikrinimui."""
    try:
        session_data = {
            'keys': list(session.keys()),
            'processed_products_count': len(session.get('processed_products', [])),
            'transport_total': session.get('transport_total'),
            'has_processed_products': 'processed_products' in session
        }
        
        # Jei yra produktų, parodyk pirmą kaip pavyzdį
        products = session.get('processed_products', [])
        if products:
            first_product = products[0]
            session_data['first_product_sample'] = {
                'name': first_product.get('name'),
                'has_banderole_type': 'banderole_type' in first_product,
                'banderole_type': first_product.get('banderole_type'),
                'keys': list(first_product.keys())
            }
        
        return jsonify(session_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test_vmi', methods=['GET'])
def test_vmi():
    """Testinis VMI generavimas su fiksuotais duomenimis."""
    try:
        # Testiniai duomenys
        test_products = [
            {
                'name': 'Test Champagne',
                'quantity': 6,
                'volume': 0.75,
                'abv': 12.0,
                'excise_category_key': 'sparkling_wine'
            }
        ]
        
        # Priskirti banderoles
        products_with_banderoles = enrich_products_with_banderoles(test_products)
        
        # Generuoti VMI failus
        from datetime import date
        period_start = date.today()
        period_end = date.today()
        
        bac_file, aah_file = generate_vmi_files_for_products(
            products_with_banderoles, period_start, period_end, app.config['OUTPUT_FOLDER']
        )
        
        return jsonify({
            'success': True,
            'products_count': len(products_with_banderoles),
            'bac_file': bac_file,
            'aah_file': aah_file,
            'first_product': products_with_banderoles[0] if products_with_banderoles else None
        })
        
    except Exception as e:
        logging.error(f"Test VMI klaida: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/debug_session')
def debug_session_route():
    """Debug route session duomenų tikrinimui."""
    try:
        session_data = {
            'processed_products': session.get('processed_products', []),
            'transport_total': session.get('transport_total', 0),
            'session_keys': list(session.keys())
        }
        
        products = session_data['processed_products']
        
        result = {
            'session_data': session_data,
            'products_count': len(products),
            'first_product': products[0] if products else None,
            'has_banderole_info': bool(products and products[0].get('banderole_type')) if products else False
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download_vmi/<banderole_type>')
def download_vmi_file(banderole_type):
    """Atsisiųsti esamą VMI failą."""
    try:
        banderoles_dir = 'Banderolių apskaita'
        
        if banderole_type == 'BAC':
            filename = 'BAC.csv'
        elif banderole_type == 'AAH':
            filename = 'AAH.csv'
        else:
            flash("Neteisingas banderolės tipas.", "error")
            return redirect(url_for('main_route'))
        
        file_path = os.path.join(banderoles_dir, filename)
        
        if os.path.exists(file_path):
            return send_from_directory(banderoles_dir, filename, as_attachment=True)
        else:
            flash(f"Failas {filename} nerastas.", "error")
            return redirect(url_for('main_route'))
            
    except Exception as e:
        logging.error(f"Klaida atsisiunčiant VMI failą: {e}")
        flash(f"Klaida atsisiunčiant failą: {e}", "error")
        return redirect(url_for('main_route'))

@app.route('/debug_web')
def debug_web_route():
    """Debug puslapis web sąsajai."""
    try:
        session_data = {
            'processed_products': session.get('processed_products', []),
            'transport_total': session.get('transport_total', 0),
            'session_keys': list(session.keys())
        }
        
        products = session_data['processed_products']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug Web Sąsaja</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .info {{ background: #e7f3ff; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ background: #d4edda; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .error {{ background: #f8d7da; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                button {{ padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }}
                button:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <h1>Debug Web Sąsaja</h1>
            
            <div class="info">
                <h3>Session informacija:</h3>
                <p><strong>Produktų kiekis:</strong> {len(products)}</p>
                <p><strong>Session raktai:</strong> {', '.join(session_data['session_keys'])}</p>
                <p><strong>Transporto suma:</strong> {session_data['transport_total']}€</p>
                <p><strong>Turi banderolių info:</strong> {bool(products and products[0].get('banderole_type')) if products else False}</p>
            </div>
            
            {f'<div class="success"><h3>Pirmas produktas:</h3><pre>{products[0]}</pre></div>' if products else '<div class="error">Nėra produktų session\'e</div>'}
            
            <div>
                <h3>Veiksmai:</h3>
                <button onclick="location.href='/'">Grįžti į pagrindinį</button>
                <button onclick="location.href='/simulate_invoice'" id="simulateBtn">Imituoti sąskaitą</button>
                <button onclick="testVMI()">Testuoti VMI</button>
                <button onclick="location.reload()">Atnaujinti</button>
            </div>
            
            <div id="result"></div>
            
            <script>
                // Imituoti sąskaitos apdorojimą
                document.getElementById('simulateBtn').onclick = function() {{
                    fetch('/simulate_invoice', {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="success">Sąskaita imituota: ' + JSON.stringify(data) + '</div>';
                        setTimeout(() => location.reload(), 1000);
                    }})
                    .catch(error => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="error">Klaida: ' + error + '</div>';
                    }});
                }};
                
                // Testuoti VMI generavimą
                function testVMI() {{
                    const formData = new FormData();
                    formData.append('period_start', '2025-01-09');
                    formData.append('period_end', '2025-01-10');
                    formData.append('banderole_type', 'both');
                    
                    fetch('/generate_vmi', {{
                        method: 'POST',
                        body: formData
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            document.getElementById('result').innerHTML = 
                                '<div class="success">VMI failai sugeneruoti sėkmingai!</div>';
                        }} else {{
                            return response.text().then(text => {{
                                document.getElementById('result').innerHTML = 
                                    '<div class="error">VMI klaida: ' + text.substring(0, 200) + '</div>';
                            }});
                        }}
                    }})
                    .catch(error => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="error">VMI klaida: ' + error + '</div>';
                    }});
                }}
            </script>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Debug klaida</h1><pre>{str(e)}</pre>", 500

@app.route('/simulate_invoice', methods=['POST'])
def simulate_invoice_route():
    """Imituoja sąskaitos apdorojimą su testiniais duomenimis."""
    try:
        # Sukurti testinius produktus (imituoja extract_invoice_data rezultatą)
        test_products = [
            {
                'name': 'Champagne Brut Premium 0.75L',
                'quantity': 12,
                'volume': 0.75,
                'abv': 12.5,
                'unit_price': 25.50,
                'amount': 306.00
            },
            {
                'name': 'Bordeaux Rouge AOC 0.75L',
                'quantity': 6,
                'volume': 0.75,
                'abv': 13.5,
                'unit_price': 18.90,
                'amount': 113.40
            }
        ]
        
        logging.info(f"Imituojamas sąskaitos apdorojimas su {len(test_products)} produktais")
        
        # Papildyti akcizo informacija
        enriched_products = enrich_products_with_excise(test_products)
        logging.info(f"Po akcizo papildymo: {len(enriched_products)} produktų")
        
        # Papildyti banderolių informacija
        products_with_banderoles = enrich_products_with_banderoles(enriched_products)
        logging.info(f"Po banderolių priskyrimo: {len(products_with_banderoles)} produktų")
        
        # Išsaugoti session
        session['processed_products'] = products_with_banderoles
        session['transport_total'] = 50.0  # Testinis transportas
        
        logging.info(f"Išsaugota {len(products_with_banderoles)} produktų session'e")
        
        return jsonify({
            'success': True,
            'products_count': len(products_with_banderoles),
            'message': 'Testiniai duomenys išsaugoti session\'e'
        })
        
    except Exception as e:
        logging.error(f"Klaida imituojant sąskaitą: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/cache/stats')
def cache_stats():
    """Grąžina cache statistiką."""
    try:
        stats = pdf_cache.get_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error("Klaida gaunant cache statistiką: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Išvalo cache."""
    try:
        removed_count = pdf_cache.clear()
        return jsonify({
            "success": True,
            "message": f"Cache išvalytas: pašalinta {removed_count} failų",
            "removed_files": removed_count
        })
    except Exception as e:
        logging.error("Klaida valant cache: %s", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/debug_vmi_detailed')
def debug_vmi_detailed():
    """Detailed debug route for VMI issues."""
    try:
        import logging
        import json
        from datetime import date
        from generate_vmi import append_to_existing_vmi_files
        from banderoles import enrich_products_with_banderoles
        
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        
        # Get products from session
        products = session.get('processed_products', [])
        logger.info(f"DEBUG VMI: Found {len(products)} products in session")
        
        # Detailed product analysis
        debug_info = []
        debug_info.append(f"Total products: {len(products)}")
        
        if not products:
            debug_info.append("ERROR: No products found in session!")
            return "<pre>" + "\n".join(debug_info) + "</pre>"
        
        # Check each product
        for i, product in enumerate(products[:3]):  # Check first 3 products
            debug_info.append(f"\nProduct {i+1}:")
            debug_info.append(f"  Name: {product.get('name', 'MISSING')}")
            debug_info.append(f"  Has banderole_type: {'banderole_type' in product}")
            debug_info.append(f"  Banderole type: {product.get('banderole_type', 'MISSING')}")
            debug_info.append(f"  Banderole count: {product.get('banderole_count', 'MISSING')}")
            debug_info.append(f"  Keys: {list(product.keys())}")
        
        # Check for products without banderole info
        products_without_banderoles = [p for p in products if not p.get('banderole_type')]
        debug_info.append(f"\nProducts without banderole info: {len(products_without_banderoles)}")
        
        # Try enrichment if needed
        if products_without_banderoles:
            debug_info.append("Attempting to enrich products...")
            try:
                products = enrich_products_with_banderoles(products)
                debug_info.append("Enrichment successful")
            except Exception as e:
                debug_info.append(f"Enrichment failed: {str(e)}")
                return "<pre>" + "\n".join(debug_info) + "</pre>"
        
        # Test VMI function directly
        debug_info.append("\nTesting VMI function...")
        try:
            # Use recent dates for testing
            period_start = date.today()
            period_end = date.today()
            
            # Call the function and capture detailed results
            success_bac, success_aah = append_to_existing_vmi_files(
                products, period_start, period_end
            )
            
            debug_info.append(f"VMI function returned: BAC={success_bac}, AAH={success_aah}")
            debug_info.append(f"BAC type: {type(success_bac)}, AAH type: {type(success_aah)}")
            
            # Check the exact condition that causes the error
            files_updated = []
            if success_bac:
                files_updated.append("BAC.csv")
            if success_aah:
                files_updated.append("AAH.csv")
            
            if files_updated:
                debug_info.append(f"SUCCESS: Files updated - {', '.join(files_updated)}")
            else:
                debug_info.append(f"FAILURE: No files updated. BAC={success_bac} (bool={bool(success_bac)}), AAH={success_aah} (bool={bool(success_aah)})")
                
        except Exception as e:
            debug_info.append(f"VMI function exception: {str(e)}")
            import traceback
            debug_info.append(f"Traceback: {traceback.format_exc()}")
        
        return "<pre>" + "\n".join(debug_info) + "</pre>"
        
    except Exception as e:
        return f"<pre>Debug route error: {str(e)}\n{traceback.format_exc()}</pre>"

if __name__ == "__main__":
    import webbrowser
    import threading
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:5000")
    
    # Debug režimas - naudojame Flask development serverį
    print("--- Bandau paleisti Flask aplikaciją ---")
    print(f" * Debug režimas yra: {app.debug}")
    print(" * Terminale turėtumėte matyti daugiau pranešimų...")
    
    # Start browser opener in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(host="127.0.0.1", port=5000, debug=True)