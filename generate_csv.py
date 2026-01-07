import pandas as pd
from io import StringIO
import logging
import csv

def get_column_map_for_csv():
    """ Grąžina stulpelių žemėlapį (originalus raktas -> nauja antraštė). """
    return [
        ("name", "Prekės pavadinimas"),
        ("volume", "Tūris (L)"),
        ("abv", "Alk. %"),
        ("quantity", "Kiekis (vnt)"),
        ("unit_price", "Vnt. kaina (€)"),
        ("unit_price_with_discount", "Vnt. kaina su nuolaida (€)"),
        ("discount_percentage", "Nuolaida (%)"),
        ("amount", "Suma (€)"),
        ("amount_with_discount", "Suma su nuolaida (€)"),
        ("excise_category", "Akcizo kategorija"),
        ("excise_per_unit", "Akcizas vnt. (€)"),
        ("excise_total", "Akcizas viso (€)"),
        ("transport_per_unit", "Transportas vnt. (€)"),
        ("transport_total", "Transportas viso (€)"),
        ("cost_wo_vat", "Savikaina vnt. be PVM (€)"),
        ("cost_w_vat", "Savikaina vnt. su PVM (€)"),
        ("cost_wo_vat_total", "Savikaina viso be PVM (€)"),
        ("cost_w_vat_total", "Savikaina viso su PVM (€)"),
    ]

def generate_csv_string(products_data: list) -> str:
    if not products_data:
        logging.warning("generate_csv_string gavo tuščią products_data sąrašą.")
        return ""

    df = pd.DataFrame(products_data)
    logging.debug(f"DataFrame CSV generavimui (prieš stulpelių tvarkymą): \n{df.head()}")

    columns_map = get_column_map_for_csv()
    
    df_export = pd.DataFrame()
    final_ordered_headers = []

    for original_key, new_header in columns_map:
        if original_key in df.columns:
            df_export[new_header] = df[original_key]
            final_ordered_headers.append(new_header)
        else:
            df_export[new_header] = pd.Series([None] * len(df), name=new_header)
            final_ordered_headers.append(new_header)
            logging.warning(f"CSV generavime nerastas stulpelis su raktu: '{original_key}'. Sukurtas tuščias stulpelis '{new_header}'.")
    
    df = df_export[final_ordered_headers]

    # Sumų eilutė
    sums = {}
    if final_ordered_headers:
        sums[final_ordered_headers[0]] = "Iš viso"

    columns_to_sum_by_header = [
        "Kiekis (vnt)", "Suma (€)", "Suma su nuolaida (€)", "Akcizas viso (€)", 
        "Transportas viso (€)", "Savikaina viso be PVM (€)", "Savikaina viso su PVM (€)"
    ]

    for col_header in final_ordered_headers:
        if col_header == final_ordered_headers[0]:
            continue
        if col_header in columns_to_sum_by_header:
            try:
                col_sum = pd.to_numeric(df[col_header], errors='coerce').sum()
                sums[col_header] = round(col_sum, 2)
            except Exception as e:
                logging.warning(f"Klaida sumuojant stulpelį '{col_header}' CSV sumų eilutei: {e}")
                sums[col_header] = "Klaida"
        else:
            sums[col_header] = "" 
            
    sums_df = pd.DataFrame([sums], columns=df.columns)
    df_final_export = pd.concat([df, sums_df], ignore_index=True)
    
    logging.debug(f"DataFrame CSV eksportui (su sumomis): \n{df_final_export.head()}")

    csv_buffer = StringIO()
    df_final_export.to_csv(csv_buffer, index=False, sep=';', encoding='windows-1257', decimal='.', quoting=csv.QUOTE_ALL) 
    return csv_buffer.getvalue()
