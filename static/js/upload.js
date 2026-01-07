/**
 * Upload formos JavaScript funkcionalumas
 */

class UploadManager {
    constructor() {
        this.transportInput = document.getElementById('transport_total');
        this.statusDiv = document.getElementById('transport-status');
        this.fileInput = document.getElementById('file');
        this.fileUploadArea = document.querySelector('.file-upload-area');
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateTransportStatus();
    }
    
    setupEventListeners() {
        // Transporto input event listeners
        if (this.transportInput) {
            this.transportInput.addEventListener('input', () => this.updateTransportStatus());
            this.transportInput.addEventListener('change', () => this.updateTransportStatus());
        }
        
        // Drag and drop funkcionalumas
        if (this.fileUploadArea) {
            this.setupDragAndDrop();
        }
        
        // File input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.updateFileName(e.target));
        }
    }
    
    updateFileName(input) {
        const fileNameDisplay = document.getElementById('file-name-display');
        if (!fileNameDisplay) return;
        
        if (input.files && input.files.length > 0) {
            fileNameDisplay.textContent = input.files[0].name;
            fileNameDisplay.classList.add('file-selected');
        } else {
            fileNameDisplay.textContent = 'Nepasirinktas joks failas';
            fileNameDisplay.classList.remove('file-selected');
        }
    }
    
    updateTransportStatus() {
        if (!this.transportInput || !this.statusDiv) return;
        
        const value = parseFloat(this.transportInput.value) || 0;
        
        if (value > 0) {
            this.statusDiv.innerHTML = `
                <span class="status-icon">✏️</span>
                <span class="status-text">Naudojama įvesta suma: ${value.toFixed(2)} EUR</span>
            `;
            this.statusDiv.className = 'transport-status info';
        } else {
            this.statusDiv.innerHTML = `
                <span class="status-icon">🔍</span>
                <span class="status-text">Sistema ieškos transporto išlaidų sąskaitoje automatiškai</span>
            `;
            this.statusDiv.className = 'transport-status success';
        }
        
        this.statusDiv.style.display = 'flex';
    }
    
    setupDragAndDrop() {
        this.fileUploadArea.addEventListener('dragover', (event) => {
            event.preventDefault();
            this.fileUploadArea.classList.add('dragover');
        });

        this.fileUploadArea.addEventListener('dragleave', () => {
            this.fileUploadArea.classList.remove('dragover');
        });

        this.fileUploadArea.addEventListener('drop', (event) => {
            event.preventDefault();
            this.fileUploadArea.classList.remove('dragover');
            
            if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
                this.fileInput.files = event.dataTransfer.files;
                this.updateFileName(this.fileInput);
            }
        });
    }
}

// Inicializuojame kai DOM užkrautas
document.addEventListener('DOMContentLoaded', () => {
    new UploadManager();
});