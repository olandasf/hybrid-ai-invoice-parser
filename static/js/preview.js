/**
 * Preview puslapio JavaScript funkcionalumas
 */

class PreviewManager {
    constructor() {
        this.transportTotal = parseFloat(window.TRANSPORT_TOTAL_OVERALL) || 0;
        this.categoryLabels = window.ALL_CATEGORY_LABELS || {};
        this.columnKeys = window.COLUMN_KEYS_FOR_JS || [];
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateTotalStats();
    }
    
    setupEventListeners() {
        const recalculateAllBtn = document.getElementById('recalculateAllButton');
        if (recalculateAllBtn) {
            recalculateAllBtn.addEventListener('click', () => this.recalculateAllProducts());
        }
    }
    
    async recalculateRowData(rowIndex) {
        const rowElement = document.querySelector(`#productsTable tbody tr[data-id='${rowIndex}']`);
        if (!rowElement) {
            console.error("Nepavyko rasti eilutės su data-id: " + rowIndex);
            return;
        }
        
        console.log("Siunčiami duomenys perskaičiavimui (eilutė " + rowIndex + ")");

        try {
            const response = await fetch("/recalculate_item_data", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_index: rowIndex,
                    transport_total: this.transportTotal,
                    all_products: this.getCurrentTableData()
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("Klaida iš serverio (recalculate_item_data):", errorData);
                this.showError("Klaida perskaičiuojant eilutę: " + (errorData.error || response.statusText));
                return;
            }

            const updatedItemFromServer = await response.json();
            console.log("Gauti atnaujinti duomenys iš serverio (eilutė " + rowIndex + "):", updatedItemFromServer);

            this.updateTableRow(rowElement, updatedItemFromServer);
            this.updateTotalStats();

        } catch (error) {
            console.error("Tinklo ar JS klaida perskaičiuojant eilutę (" + rowIndex + "):", error);
            this.showError("Įvyko klaida perskaičiuojant eilutės duomenis.");
        }
    }
    
    async recalculateAllProducts() {
        const allProductsData = this.getCurrentTableData();

        console.log("Siunčiami visi duomenys perskaičiavimui ('Perskaičiuoti lentelę')");

        try {
            const response = await fetch("/recalculate_all_products", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    products: allProductsData,
                    transport_total: this.transportTotal
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("Klaida iš serverio (recalculate_all_products):", errorData);
                this.showError("Klaida perskaičiuojant visą lentelę: " + (errorData.error || response.statusText));
                return;
            }

            const updatedProductsList = await response.json();
            console.log("Gautas atnaujintas produktų sąrašas:", updatedProductsList);

            updatedProductsList.forEach((updatedItem, productIndex) => {
                const rowElement = document.querySelector(`#productsTable tbody tr[data-id='${productIndex}']`);
                if (rowElement) {
                    this.updateTableRow(rowElement, updatedItem);
                }
            });
            
            this.updateTotalStats();
            this.showSuccess("Lentelė sėkmingai perskaičiuota!");

        } catch (error) {
            console.error("Tinklo ar JS klaida perskaičiuojant visą lentelę:", error);
            this.showError("Įvyko klaida perskaičiuojant visus duomenis.");
        }
    }
    
    getCurrentTableData() {
        let allProducts = [];
        try {
            const table = document.getElementById("productsTable");
            if (!table) {
                console.error("Lentelė #productsTable nerasta");
                return [];
            }
            
            const rows = table.querySelectorAll("tbody tr");
            console.log(`Rasta ${rows.length} eilučių lentelėje`);
            
            rows.forEach((row, index) => {
                if (row.querySelector('td[colspan]')) {
                    console.log(`Praleista eilutė ${index} (sumų eilutė)`);
                    return;
                }
                
                let product = {};
                const inputs = row.querySelectorAll('input[name], select[name]');
                console.log(`Eilutėje ${index} rasta ${inputs.length} input/select elementų`);
                
                inputs.forEach(input => {
                    if (input.name) {
                        product[input.name] = input.value || '';
                    }
                });
                
                if (product.name && product.name.trim() !== '') {
                    allProducts.push(product);
                    console.log(`Pridėtas produktas ${index}:`, product.name);
                } else {
                    console.warn(`Praleistas produktas ${index} - nėra pavadinimo`);
                }
            });
            
            console.log(`Iš viso surinkta ${allProducts.length} produktų`);
            return allProducts;
            
        } catch (error) {
            console.error("Klaida renkant lentelės duomenis:", error);
            return [];
        }
    }
    
    updateTableRow(rowElement, updatedItemData) {
        rowElement.querySelectorAll('input[name], select[name]').forEach(inputOrSelect => {
            const fieldName = inputOrSelect.name;
            if (updatedItemData.hasOwnProperty(fieldName)) {
                let valueToSet = updatedItemData[fieldName];

                if (inputOrSelect.tagName === 'SELECT') {
                    inputOrSelect.value = valueToSet;
                } else {
                    if (typeof valueToSet === 'number') {
                        if (['excise_per_unit', 'transport_per_unit'].includes(fieldName)) {
                            valueToSet = valueToSet.toFixed(4);
                        } else if (['volume'].includes(fieldName)) {
                            valueToSet = valueToSet.toFixed(3);
                        } else if (['quantity'].includes(fieldName) && Number.isInteger(valueToSet)) {
                            valueToSet = valueToSet.toFixed(0);
                        } else {
                            valueToSet = valueToSet.toFixed(2);
                        }
                    }
                    inputOrSelect.value = (valueToSet !== null && valueToSet !== undefined) ? valueToSet : '';
                }
            }
        });
    }
    
    updateTotalStats() {
        let totalQuantity = 0;
        let totalPurchaseAmount = 0;
        let totalPurchaseAmountWithDiscount = 0;
        let totalExciseAmount = 0;
        let totalTransportDistributed = 0;
        let totalCostWoVat = 0;
        let totalCostWVat = 0;

        const rows = document.querySelectorAll("#productsTable tbody tr");
        rows.forEach(row => {
            if (row.querySelector('td[colspan]')) return;

            totalQuantity += parseFloat(row.querySelector('input[name="quantity"]')?.value) || 0;
            totalPurchaseAmount += parseFloat(row.querySelector('input[name="amount"]')?.value) || 0;
            totalPurchaseAmountWithDiscount += parseFloat(row.querySelector('input[name="amount_with_discount"]')?.value) || 0;
            totalExciseAmount += parseFloat(row.querySelector('input[name="excise_total"]')?.value) || 0;
            totalTransportDistributed += parseFloat(row.querySelector('input[name="transport_total"]')?.value) || 0;
            totalCostWoVat += parseFloat(row.querySelector('input[name="cost_wo_vat_total"]')?.value) || 0;
            totalCostWVat += parseFloat(row.querySelector('input[name="cost_w_vat_total"]')?.value) || 0;
        });

        this.updateStatElement('totalQuantity', Math.round(totalQuantity));
        this.updateStatElement('totalPurchaseAmount', totalPurchaseAmount.toFixed(2));
        this.updateStatElement('totalPurchaseAmountWithDiscount', totalPurchaseAmountWithDiscount.toFixed(2));
        this.updateStatElement('totalExciseAmount', totalExciseAmount.toFixed(2));
        this.updateStatElement('totalTransportAmountOverall', this.transportTotal.toFixed(2));
        this.updateStatElement('totalTransportDistributed', totalTransportDistributed.toFixed(2));
        this.updateStatElement('totalCostWoVat', totalCostWoVat.toFixed(2));
        this.updateStatElement('totalCostWVat', totalCostWVat.toFixed(2));
    }
    
    updateStatElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        // Sukuriame notification elementą
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Pridedame stilius
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 5px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Nustatome spalvą pagal tipą
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        // Pridedame į DOM
        document.body.appendChild(notification);
        
        // Pašaliname po 3 sekundžių
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Global funkcijos (backward compatibility)
function markRowForRecalculation(inputElement, rowIndex) {
    console.log("Eilutė " + rowIndex + " pakeista (lauko '" + inputElement.name + "' keitimas). Kviečiamas perskaičiavimas.");
    setTimeout(() => window.previewManager.recalculateRowData(rowIndex), 150);
}

function handleCategoryChange(selectElement, rowIndex) {
    console.log("Pakeista kategorija eilutėje", rowIndex, "į raktą:", selectElement.value);
    setTimeout(() => window.previewManager.recalculateRowData(rowIndex), 150);
}

function prepareAndSubmit(formId, inputId) {
    try {
        const tableData = window.previewManager.getCurrentTableData();
        console.log("Ruošiami duomenys Excel/CSV generavimui:", tableData);
        
        if (!tableData || tableData.length === 0) {
            window.previewManager.showError("Nėra duomenų eksportavimui. Patikrinkite ar lentelėje yra produktų.");
            return;
        }
        
        const jsonData = JSON.stringify(tableData);
        console.log("JSON duomenys:", jsonData.substring(0, 200) + "...");
        
        document.getElementById(inputId).value = jsonData;
        
        const form = document.getElementById(formId);
        if (!form) {
            window.previewManager.showError("Klaida: forma nerasta. Perkraukite puslapį ir bandykite dar kartą.");
            return;
        }
        
        console.log("Siunčiama forma:", formId);
        form.submit();
        
    } catch (error) {
        console.error("Klaida ruošiant duomenis eksportavimui:", error);
        window.previewManager.showError("Klaida ruošiant duomenis eksportavimui: " + error.message);
    }
}

// Inicializuojame kai DOM užkrautas
document.addEventListener('DOMContentLoaded', () => {
    window.previewManager = new PreviewManager();
});