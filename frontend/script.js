// Global Application State
const AppState = {
    currentSection: 'dashboard',
    currentStep: 1,
    vcfFile: null,
    selectedDrugs: [],
    analysisConfig: {
        useCohere: true,
        detailedAnalysis: true,
        includeAlternatives: true,
        includeReferences: true,
        patientFriendly: true
    },
    patientInfo: {
        id: '',
        name: '',
        notes: ''
    },
    reports: [],
    drugs: [],
    apiEndpoint: 'http://localhost:8000',
    currentJobId: null
};

// Sample drug database
const DRUG_DATABASE = [
    {
        id: 'warfarin',
        name: 'Warfarin',
        generic: 'warfarin sodium',
        category: 'cardiovascular',
        description: 'Anticoagulant medication used to prevent blood clots',
        genes: ['CYP2C9', 'VKORC1', 'CYP4F2'],
        evidenceLevel: 'high'
    },
    {
        id: 'simvastatin',
        name: 'Simvastatin',
        generic: 'simvastatin',
        category: 'cardiovascular',
        description: 'Statin medication used to lower cholesterol',
        genes: ['SLCO1B1', 'CYP3A4'],
        evidenceLevel: 'high'
    },
    {
        id: 'clopidogrel',
        name: 'Clopidogrel',
        generic: 'clopidogrel bisulfate',
        category: 'cardiovascular',
        description: 'Antiplatelet medication to prevent blood clots',
        genes: ['CYP2C19'],
        evidenceLevel: 'high'
    },
    {
        id: 'tamoxifen',
        name: 'Tamoxifen',
        generic: 'tamoxifen citrate',
        category: 'oncology',
        description: 'Selective estrogen receptor modulator for breast cancer',
        genes: ['CYP2D6'],
        evidenceLevel: 'high'
    },
    {
        id: 'codeine',
        name: 'Codeine',
        generic: 'codeine phosphate',
        category: 'pain',
        description: 'Opioid pain medication and cough suppressant',
        genes: ['CYP2D6'],
        evidenceLevel: 'high'
    },
    {
        id: 'omeprazole',
        name: 'Omeprazole',
        generic: 'omeprazole',
        category: 'other',
        description: 'Proton pump inhibitor for acid reflux',
        genes: ['CYP2C19'],
        evidenceLevel: 'medium'
    },
    {
        id: 'fluoxetine',
        name: 'Fluoxetine',
        generic: 'fluoxetine hydrochloride',
        category: 'psychiatric',
        description: 'SSRI antidepressant medication',
        genes: ['CYP2D6', 'CYP2C9'],
        evidenceLevel: 'medium'
    },
    {
        id: 'haloperidol',
        name: 'Haloperidol',
        generic: 'haloperidol',
        category: 'psychiatric',
        description: 'Typical antipsychotic medication',
        genes: ['CYP2D6'],
        evidenceLevel: 'medium'
    },
    {
        id: 'metformin',
        name: 'Metformin',
        generic: 'metformin hydrochloride',
        category: 'other',
        description: 'Diabetes medication to control blood sugar',
        genes: ['SLC22A1', 'SLC22A2'],
        evidenceLevel: 'low'
    },
    {
        id: 'ibuprofen',
        name: 'Ibuprofen',
        generic: 'ibuprofen',
        category: 'pain',
        description: 'NSAID for pain and inflammation',
        genes: ['CYP2C9'],
        evidenceLevel: 'low'
    }
];

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    setupEventListeners();
    setupCustomDrugInput();
    await loadDrugsFromAPI();
    await loadReportsFromAPI();
    updateDashboard();
    populateDrugDatabase();
    loadSettings();
}

// API Functions
async function apiCall(endpoint, options = {}) {
    try {
        const url = ${AppState.apiEndpoint}/api${endpoint};
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || HTTP ${response.status});
        }
        
        return await response.json();
    } catch (error) {
        console.error(API call failed: ${endpoint}, error);
        throw error;
    }
}

async function loadDrugsFromAPI() {
    try {
        const response = await apiCall('/drugs');
        AppState.drugs = response.drugs;
        populateAvailableDrugs();
    } catch (error) {
        console.error('Failed to load drugs:', error);
        showToast('Failed to load drug database', 'error');
        // Fallback to local drug data if API fails
        AppState.drugs = DRUG_DATABASE;
        populateAvailableDrugs();
    }
}

async function loadReportsFromAPI() {
    try {
        const response = await apiCall('/reports');
        // Map API response to frontend format
        AppState.reports = response.reports.map(apiReport => ({
            id: apiReport.id,
            jobId: apiReport.id, // Use the API report ID as jobId
            title: Analysis for ${apiReport.patient_info?.name || apiReport.patient_info?.id || 'Unknown Patient'},
            date: apiReport.created_at,
            status: apiReport.status,
            summary: Pharmacogenomics analysis for ${apiReport.drugs?.length || 0} drug(s),
            patientId: apiReport.patient_info?.id || 'Unknown',
            drugs: apiReport.drugs || [],
            variants: apiReport.result?.analysis_summary?.variants_processed || 0,
            interactions: apiReport.result?.analysis_summary?.interactions_found || 0,
            highRiskInteractions: apiReport.result?.analysis_summary?.high_risk_interactions || 0
        }));
    } catch (error) {
        console.error('Failed to load reports:', error);
        showToast('Failed to load reports', 'error');
        // Load from localStorage as fallback
        loadStoredData();
    }
}

async function uploadVcfFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Show progress for large files
        if (file.size > 100 * 1024 * 1024) { // > 100MB
            showToast(Uploading large file (${formatFileSize(file.size)}). This may take several minutes..., 'info');
        }
        
        const response = await fetch(${AppState.apiEndpoint}/api/upload-vcf, {
            method: 'POST',
            body: formData,
            // Add timeout for large files (10 minutes)
            signal: AbortSignal.timeout(600000)
        });
        
        // Get response text first to debug
        const responseText = await response.text();
        console.log('Upload response status:', response.status);
        console.log('Upload response text:', responseText);
        
        if (!response.ok) {
            let errorMessage = 'Upload failed';
            try {
                const errorData = JSON.parse(responseText);
                errorMessage = errorData.error || errorMessage;
            } catch (parseError) {
                console.error('Failed to parse error response:', parseError);
                errorMessage = Server error: ${response.status} ${response.statusText};
            }
            throw new Error(errorMessage);
        }
        
        // Parse successful response
        try {
            return JSON.parse(responseText);
        } catch (parseError) {
            console.error('Failed to parse success response:', parseError);
            console.error('Response text was:', responseText);
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        if (error.name === 'TimeoutError') {
            throw new Error('Upload timed out. Please try with a smaller file or check your connection.');
        }
        console.error('VCF upload failed:', error);
        throw error;
    }
}

async function startAnalysisAPI() {
    try {
        const analysisData = {
            vcf_file: AppState.vcfFile.filepath,
            drugs: AppState.selectedDrugs.map(drug => drug.id),
            drug_details: AppState.selectedDrugs.map(drug => ({
                id: drug.id,
                name: drug.name,
                isCustom: drug.isCustom || false
            })),
            patient_info: AppState.patientInfo,
            config: AppState.analysisConfig
        };
        
        const response = await apiCall('/start-analysis', {
            method: 'POST',
            body: JSON.stringify(analysisData)
        });
        
        return response;
    } catch (error) {
        console.error('Failed to start analysis:', error);
        throw error;
    }
}

async function checkAnalysisStatus(jobId) {
    try {
        return await apiCall(/analysis-status/${jobId});
    } catch (error) {
        console.error('Failed to check analysis status:', error);
        throw error;
    }
}

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', handleNavigation);
    });

    // VCF File Upload
    const vcfFileInput = document.getElementById('vcf-file');
    const vcfUploadArea = document.getElementById('vcf-upload-area');
    
    if (vcfFileInput) {
        vcfFileInput.addEventListener('change', handleVcfFileSelect);
    }
    
    if (vcfUploadArea) {
        vcfUploadArea.addEventListener('dragover', handleDragOver);
        vcfUploadArea.addEventListener('drop', handleDrop);
        vcfUploadArea.addEventListener('click', () => vcfFileInput?.click());
    }

    // Drug Search and Selection
    const drugSearch = document.getElementById('drug-search');
    if (drugSearch) {
        drugSearch.addEventListener('input', handleDrugSearch);
    }

    // Category buttons
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', handleCategoryFilter);
    });

    // Form inputs
    const patientIdInput = document.getElementById('patient-id');
    const patientNameInput = document.getElementById('patient-name');
    const analysisNotesInput = document.getElementById('analysis-notes');

    if (patientIdInput) {
        patientIdInput.addEventListener('input', (e) => {
            AppState.patientInfo.id = e.target.value;
        });
    }

    if (patientNameInput) {
        patientNameInput.addEventListener('input', (e) => {
            AppState.patientInfo.name = e.target.value;
        });
    }

    if (analysisNotesInput) {
        analysisNotesInput.addEventListener('input', (e) => {
            AppState.patientInfo.notes = e.target.value;
        });
    }

    // Configuration checkboxes
    document.querySelectorAll('#step-4 input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleConfigChange);
    });

    // Reports search and filter
    const reportSearch = document.getElementById('report-search');
    const reportFilter = document.getElementById('report-filter');

    if (reportSearch) {
        reportSearch.addEventListener('input', handleReportSearch);
    }

    if (reportFilter) {
        reportFilter.addEventListener('change', handleReportFilter);
    }

    // View options
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', handleViewChange);
    });

    // Drug database search and filters
    const drugDbSearch = document.getElementById('drug-db-search');
    const drugCategoryFilter = document.getElementById('drug-category-filter');
    const drugEvidenceFilter = document.getElementById('drug-evidence-filter');

    if (drugDbSearch) {
        drugDbSearch.addEventListener('input', handleDrugDbSearch);
    }

    if (drugCategoryFilter) {
        drugCategoryFilter.addEventListener('change', handleDrugDbFilter);
    }

    if (drugEvidenceFilter) {
        drugEvidenceFilter.addEventListener('change', handleDrugDbFilter);
    }

    // Settings
    document.querySelectorAll('#settings input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleSettingsChange);
    });

    const apiEndpointInput = document.getElementById('api-endpoint');
    if (apiEndpointInput) {
        apiEndpointInput.addEventListener('change', (e) => {
            AppState.apiEndpoint = e.target.value;
            saveSettings();
        });
    }

    // Modal close events
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });

    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// Navigation Functions
function handleNavigation(e) {
    e.preventDefault();
    const section = e.target.closest('.nav-link').dataset.section;
    switchSection(section);
}

function switchSection(sectionName) {
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector([data-section="${sectionName}"]);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // Update content
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });

    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
        AppState.currentSection = sectionName;
    }

    // Load section-specific data
    switch (sectionName) {
        case 'dashboard':
            updateDashboard();
            break;
        case 'analysis':
            // Don't automatically reset - preserve current progress
            // Only reset if explicitly requested or if starting fresh
            if (AppState.currentStep === 0 || !AppState.currentStep) {
                resetAnalysisForm();
            } else {
                // Restore to current step
                showStep(AppState.currentStep);
            }
            break;
        case 'reports':
            loadReports();
            break;
        case 'drugs':
            populateDrugDatabase();
            break;
        case 'settings':
            loadSettings();
            break;
    }
}

// Analysis Step Functions
function startNewAnalysis() {
    // Explicitly reset the form and start fresh
    resetAnalysisForm();
    switchSection('analysis');
}

function nextStep(stepNumber) {
    if (validateCurrentStep()) {
        showStep(stepNumber);
    }
}

function previousStep(stepNumber) {
    showStep(stepNumber);
}

function showStep(stepNumber) {
    document.querySelectorAll('.analysis-step').forEach(step => {
        step.classList.remove('active');
    });

    const targetStep = document.getElementById(step-${stepNumber});
    if (targetStep) {
        targetStep.classList.add('active');
        AppState.currentStep = stepNumber;
    }
}

function validateCurrentStep() {
    switch (AppState.currentStep) {
        case 1:
            return validatePatientInfo();
        case 2:
            return validateVcfFile();
        case 3:
            return validateDrugSelection();
        case 4:
            return true; // Configuration is optional
        default:
            return true;
    }
}

function validatePatientInfo() {
    const patientId = document.getElementById('patient-id').value.trim();
    if (!patientId) {
        showToast('Please enter a patient ID', 'error');
        return false;
    }
    return true;
}

function validateVcfFile() {
    if (!AppState.vcfFile) {
        showToast('Please upload a VCF file', 'error');
        return false;
    }
    return true;
}

function validateDrugSelection() {
    if (AppState.selectedDrugs.length === 0) {
        showToast('Please select at least one drug for analysis', 'error');
        return false;
    }
    return true;
}

function resetAnalysisForm() {
    AppState.currentStep = 1;
    AppState.vcfFile = null;
    AppState.selectedDrugs = [];
    
    showStep(1);
    
    // Reset form fields
    document.getElementById('patient-id').value = '';
    document.getElementById('patient-name').value = '';
    document.getElementById('analysis-notes').value = '';
    
    // Reset custom drug input
    const customDrugInput = document.getElementById('custom-drug-name');
    if (customDrugInput) {
        customDrugInput.value = '';
    }
    
    // Reset file upload
    const vcfFileInfo = document.getElementById('vcf-file-info');
    if (vcfFileInfo) {
        vcfFileInfo.style.display = 'none';
    }
    
    // Reset drug selection
    updateSelectedDrugs();
    populateAvailableDrugs();
}

// File Upload Functions
function handleVcfFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        processVcfFile(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.target.closest('.upload-area').classList.add('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.target.closest('.upload-area').classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processVcfFile(files[0]);
    }
}

async function processVcfFile(file) {
    try {
        // Show validation in progress
        const validationElement = document.getElementById('vcf-validation');
        validationElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Uploading and validating file...</span>';
        
        // Upload file to server
        const uploadResult = await uploadVcfFile(file);
        
        // Store file info
        AppState.vcfFile = {
            name: file.name,
            size: file.size,
            filepath: uploadResult.filepath,
            filename: uploadResult.filename
        };
        
        // Update UI
        document.getElementById('vcf-filename').textContent = file.name;
        document.getElementById('vcf-filesize').textContent = formatFileSize(file.size);
        document.getElementById('vcf-file-info').style.display = 'block';
        
        // Show success validation
        validationElement.innerHTML = '<i class="fas fa-check-circle" style="color: var(--success);"></i> <span>File validated successfully</span>';
        
        // Enable next button
        document.getElementById('vcf-next-btn').disabled = false;
        
        showToast('VCF file uploaded successfully', 'success');
        
    } catch (error) {
        console.error('Error processing VCF file:', error);
        
        // Show error validation
        const validationElement = document.getElementById('vcf-validation');
        validationElement.innerHTML = <i class="fas fa-exclamation-circle" style="color: var(--danger);"></i> <span>Error: ${error.message}</span>;
        
        // Disable next button
        document.getElementById('vcf-next-btn').disabled = true;
        
        showToast(Upload failed: ${error.message}, 'error');
    }
}

function removeVcfFile() {
    AppState.vcfFile = null;
    document.getElementById('vcf-file-info').style.display = 'none';
    document.getElementById('vcf-file').value = '';
    document.getElementById('vcf-next-btn').disabled = true;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Drug Selection Functions
function populateAvailableDrugs(filteredDrugs = null) {
    const container = document.getElementById('available-drugs');
    if (!container) return;

    const drugsToShow = filteredDrugs || AppState.drugs;
    container.innerHTML = '';

    drugsToShow.forEach(drug => {
        const isSelected = AppState.selectedDrugs.some(selected => selected.id === drug.id);
        const drugElement = createDrugElement(drug, isSelected);
        container.appendChild(drugElement);
    });
}

function updateSelectedDrugs() {
    const container = document.getElementById('selected-drug-list');
    const countElement = document.getElementById('selected-count');
    
    if (!container || !countElement) return;

    container.innerHTML = '';
    countElement.textContent = AppState.selectedDrugs.length;
    
    AppState.selectedDrugs.forEach(drug => {
        const drugElement = createDrugElement(drug, true);
        container.appendChild(drugElement);
    });

    // Update next button state
    const nextBtn = document.getElementById('drug-next-btn');
    if (nextBtn) {
        nextBtn.disabled = AppState.selectedDrugs.length === 0;
    }
}

function createDrugElement(drug, isSelected) {
    const div = document.createElement('div');
    div.className = drug-item ${drug.isCustom ? 'custom-drug' : ''};
    div.onclick = () => toggleDrugSelection(drug);
    
    const customIcon = drug.isCustom ? '<i class="fas fa-user-plus" style="color: var(--accent-color); margin-right: 0.5rem;"></i>' : '';
    const evidenceClass = drug.evidenceLevel === 'unknown' ? 'custom' : drug.evidenceLevel;
    
    div.innerHTML = `
        <div class="drug-info">
            <h4>${customIcon}${drug.name}</h4>
            <p>${drug.description}</p>
        </div>
        <div class="drug-category ${evidenceClass}">${drug.isCustom ? 'custom' : drug.category}</div>
    `;
    
    return div;
}

function toggleDrugSelection(drug) {
    const index = AppState.selectedDrugs.findIndex(selected => selected.id === drug.id);
    
    if (index === -1) {
        // Add drug
        AppState.selectedDrugs.push(drug);
    } else {
        // Remove drug
        AppState.selectedDrugs.splice(index, 1);
    }
    
    updateSelectedDrugs();
    populateAvailableDrugs();
}

function handleDrugSearch(e) {
    const query = e.target.value.toLowerCase();
    const filteredDrugs = DRUG_DATABASE.filter(drug => 
        drug.name.toLowerCase().includes(query) ||
        drug.generic.toLowerCase().includes(query) ||
        drug.description.toLowerCase().includes(query)
    );
    populateAvailableDrugs(filteredDrugs);
}

function handleCategoryFilter(e) {
    // Update active category button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    e.target.classList.add('active');
    
    const category = e.target.dataset.category;
    let filteredDrugs;
    
    if (category === 'all') {
        filteredDrugs = DRUG_DATABASE;
    } else {
        filteredDrugs = DRUG_DATABASE.filter(drug => drug.category === category);
    }
    
    populateAvailableDrugs(filteredDrugs);
}

// Custom Drug Functions
function addCustomDrug() {
    const customDrugInput = document.getElementById('custom-drug-name');
    const drugName = customDrugInput.value.trim();
    
    if (!drugName) {
        showToast('Please enter a drug name', 'error');
        return;
    }
    
    // Check if drug already exists in selected drugs
    const existingDrug = AppState.selectedDrugs.find(drug => 
        drug.name.toLowerCase() === drugName.toLowerCase() ||
        drug.generic.toLowerCase() === drugName.toLowerCase()
    );
    
    if (existingDrug) {
        showToast('This drug is already selected', 'warning');
        customDrugInput.value = '';
        return;
    }
    
    // Check if drug exists in database
    const databaseDrug = AppState.drugs.find(drug => 
        drug.name.toLowerCase() === drugName.toLowerCase() ||
        drug.generic.toLowerCase() === drugName.toLowerCase()
    );
    
    if (databaseDrug) {
        // Add from database
        AppState.selectedDrugs.push(databaseDrug);
        showToast(Added ${databaseDrug.name} from database, 'success');
    } else {
        // Create custom drug entry
        const customDrug = {
            id: custom_${Date.now()},
            name: drugName,
            generic: drugName.toLowerCase(),
            category: 'custom',
            description: 'Custom drug added by user',
            genes: ['Unknown'],
            evidenceLevel: 'unknown',
            isCustom: true
        };
        
        AppState.selectedDrugs.push(customDrug);
        showToast(Added custom drug: ${drugName}, 'success');
    }
    
    // Clear input and update UI
    customDrugInput.value = '';
    updateSelectedDrugs();
    populateAvailableDrugs();
}

// Add event listener for Enter key in custom drug input
function setupCustomDrugInput() {
    const customDrugInput = document.getElementById('custom-drug-name');
    if (customDrugInput) {
        customDrugInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addCustomDrug();
            }
        });
    }
}

// Configuration Functions
function handleConfigChange(e) {
    const configKey = e.target.id.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    AppState.analysisConfig[configKey] = e.target.checked;
}

// Analysis Functions
async function startAnalysis() {
    if (!validateCurrentStep()) {
        showToast('Please complete all required fields', 'error');
        return;
    }

    // Hide step 4 and show progress
    document.getElementById('step-4').classList.remove('active');
    document.getElementById('analysis-progress').style.display = 'block';
    
    // Start the analysis process
    await runAnalysis();
}

async function runAnalysis() {
    try {
        // Update progress
        updateProgress(10, 'Starting analysis...', 'Preparing analysis request...');
        
        // Start analysis on server
        const analysisResponse = await startAnalysisAPI();
        AppState.currentJobId = analysisResponse.job_id;
        
        updateProgress(20, 'Analysis queued...', Job ID: ${AppState.currentJobId});
        
        // Poll for status updates
        await pollAnalysisStatus();
        
    } catch (error) {
        console.error('Analysis failed:', error);
        showToast(Analysis failed: ${error.message}, 'error');
        
        // Reset to step 4
        document.getElementById('analysis-progress').style.display = 'none';
        document.getElementById('step-4').classList.add('active');
    }
}

async function pollAnalysisStatus() {
    const maxAttempts = 120; // 10 minutes with 5-second intervals
    let attempts = 0;
    
    const poll = async () => {
        try {
            attempts++;
            const status = await checkAnalysisStatus(AppState.currentJobId);
            
            // Update progress based on status
            if (status.status === 'running') {
                updateProgress(
                    Math.min(30 + status.progress * 0.6, 90), 
                    'Analysis in progress...', 
                    'Processing genetic variants and drug interactions...'
                );
            } else if (status.status === 'completed') {
                updateProgress(100, 'Analysis completed!', 'Generating report...');
                
                // Add to reports
                const report = {
                    id: status.id,
                    patientId: AppState.patientInfo.id,
                    patientName: AppState.patientInfo.name || 'Unknown',
                    title: Pharmacogenomics Report - ${AppState.patientInfo.id},
                    date: status.created_at,
                    status: 'completed',
                    drugs: AppState.selectedDrugs.map(drug => drug.name),
                    variants: status.result?.analysis_summary?.variants_processed || 0,
                    interactions: status.result?.analysis_summary?.interactions_found || 0,
                    highRiskInteractions: status.result?.analysis_summary?.high_risk_interactions || 0,
                    summary: Analysis of ${AppState.selectedDrugs.length} drugs completed successfully.,
                    config: { ...AppState.analysisConfig },
                    notes: AppState.patientInfo.notes,
                    jobId: status.id
                };
                
                AppState.reports.unshift(report);
                
                setTimeout(() => {
                    switchSection('reports');
                    showToast('Analysis completed successfully!', 'success');
                    resetAnalysisForm();
                }, 1000);
                
                return;
            } else if (status.status === 'failed') {
                const errorMessage = status.error || 'Analysis failed with unknown error';
                console.error('Analysis failed:', errorMessage);
                throw new Error(errorMessage);
            }
            
            // Continue polling if still running and haven't exceeded max attempts
            if (status.status === 'running' && attempts < maxAttempts) {
                setTimeout(poll, 5000); // Poll every 5 seconds
            } else if (attempts >= maxAttempts) {
                throw new Error('Analysis timed out after 10 minutes. Please try again with a smaller VCF file or fewer drugs.');
            }
            
        } catch (error) {
            console.error('Error polling analysis status:', error);
            
            // Provide more specific error messages
            let errorMessage = error.message;
            if (error.message.includes('Failed to locate')) {
                errorMessage = 'Python environment error. Please ensure Python 3 is properly installed and accessible.';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Analysis timed out. This may happen with large VCF files. Please try again or contact support.';
            } else if (error.message.includes('Network')) {
                errorMessage = 'Network connection error. Please check your connection and try again.';
            }
            
            showToast(Analysis error: ${errorMessage}, 'error');
            
            // Reset to step 4
            document.getElementById('analysis-progress').style.display = 'none';
            document.getElementById('step-4').classList.add('active');
        }
    };
    
    // Start polling
    setTimeout(poll, 2000); // Initial delay
}

function updateProgress(percentage, text, details) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressDetails = document.getElementById('progress-details');
    
    if (progressFill) progressFill.style.width = ${percentage}%;
    if (progressText) progressText.textContent = text;
    if (progressDetails) progressDetails.textContent = details;
}

// Dashboard Functions
function updateDashboard() {
    updateDashboardStats();
    updateRecentReports();
}

function updateDashboardStats() {
    const totalReports = AppState.reports.length;
    const totalVariants = AppState.reports.reduce((sum, report) => sum + (report.variants || 0), 0);
    const totalDrugs = AppState.reports.reduce((sum, report) => sum + (report.drugs?.length || 0), 0);
    const highRiskInteractions = AppState.reports.reduce((sum, report) => sum + (report.highRiskInteractions || 0), 0);

    document.getElementById('total-reports').textContent = totalReports;
    document.getElementById('total-variants').textContent = totalVariants.toLocaleString();
    document.getElementById('total-drugs').textContent = totalDrugs;
    document.getElementById('high-risk-interactions').textContent = highRiskInteractions;
}

function updateRecentReports() {
    const container = document.getElementById('recent-reports');
    if (!container) return;

    const recentReports = AppState.reports.slice(0, 3);
    
    if (recentReports.length === 0) {
        container.innerHTML = '<p class="text-secondary">No reports available. <a href="#" onclick="switchSection(\'analysis\')">Create your first analysis</a></p>';
        return;
    }

    container.innerHTML = '';
    recentReports.forEach(report => {
        const reportCard = createReportCard(report);
        container.appendChild(reportCard);
    });
}

// Reports Functions
function loadReports() {
    const container = document.getElementById('reports-container');
    if (!container) return;

    if (AppState.reports.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
                <i class="fas fa-file-medical" style="font-size: 3rem; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No Reports Available</h3>
                <p class="text-secondary">Start by creating your first pharmacogenomics analysis</p>
                <button class="btn primary" onclick="switchSection('analysis')" style="margin-top: 1rem;">
                    <i class="fas fa-plus"></i>
                    New Analysis
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = '';
    AppState.reports.forEach(report => {
        const reportCard = createReportCard(report);
        container.appendChild(reportCard);
    });
}

function createReportCard(report) {
    const div = document.createElement('div');
    div.className = 'report-card';
    div.onclick = () => openReportModal(report);
    
    const statusClass = report.status === 'completed' ? 'completed' : 
                       report.status === 'processing' ? 'processing' : 
                       report.highRiskInteractions > 3 ? 'high-risk' : 'completed';
    
    div.innerHTML = `
        <div class="report-header">
            <div>
                <div class="report-title">${report.title}</div>
                <div class="report-date">${new Date(report.date).toLocaleDateString()}</div>
            </div>
            <div class="report-status ${statusClass}">${report.status}</div>
        </div>
        <div class="report-summary">
            <p>${report.summary}</p>
        </div>
        <div class="report-stats">
            <div class="report-stat">
                <div class="value">${report.drugs?.length || 0}</div>
                <div class="label">Drugs</div>
            </div>
            <div class="report-stat">
                <div class="value">${report.variants || 0}</div>
                <div class="label">Variants</div>
            </div>
            <div class="report-stat">
                <div class="value">${report.interactions || 0}</div>
                <div class="label">Interactions</div>
            </div>
        </div>
        <div class="report-actions">
            <button class="btn secondary" onclick="event.stopPropagation(); downloadReport('${report.id}')">
                <i class="fas fa-download"></i>
                Download
            </button>
            <button class="btn secondary" onclick="event.stopPropagation(); viewFullReport('${report.jobId || report.id}')">
                <i class="fas fa-external-link-alt"></i>
                View Full Report
            </button>
            <button class="btn primary" onclick="event.stopPropagation(); openReportModal('${report.id}')">
                <i class="fas fa-eye"></i>
                View Summary
            </button>
        </div>
    `;
    
    return div;
}

function handleReportSearch(e) {
    const query = e.target.value.toLowerCase();
    const filteredReports = AppState.reports.filter(report => 
        report.title.toLowerCase().includes(query) ||
        report.patientId.toLowerCase().includes(query) ||
        report.summary.toLowerCase().includes(query)
    );
    displayFilteredReports(filteredReports);
}

function handleReportFilter(e) {
    const filter = e.target.value;
    let filteredReports;
    
    switch (filter) {
        case 'recent':
            const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
            filteredReports = AppState.reports.filter(report => new Date(report.date) > thirtyDaysAgo);
            break;
        case 'high-risk':
            filteredReports = AppState.reports.filter(report => report.highRiskInteractions > 3);
            break;
        case 'completed':
            filteredReports = AppState.reports.filter(report => report.status === 'completed');
            break;
        case 'processing':
            filteredReports = AppState.reports.filter(report => report.status === 'processing');
            break;
        default:
            filteredReports = AppState.reports;
    }
    
    displayFilteredReports(filteredReports);
}

function displayFilteredReports(reports) {
    const container = document.getElementById('reports-container');
    if (!container) return;

    container.innerHTML = '';
    reports.forEach(report => {
        const reportCard = createReportCard(report);
        container.appendChild(reportCard);
    });
}

function handleViewChange(e) {
    document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    
    const view = e.target.dataset.view;
    const container = document.getElementById('reports-container');
    
    if (view === 'list') {
        container.classList.add('list-view');
    } else {
        container.classList.remove('list-view');
    }
}

// Drug Database Functions
function populateDrugDatabase() {
    const container = document.getElementById('drug-database-grid');
    if (!container) return;

    container.innerHTML = '';
    DRUG_DATABASE.forEach(drug => {
        const drugCard = createDrugCard(drug);
        container.appendChild(drugCard);
    });
}

function createDrugCard(drug) {
    const div = document.createElement('div');
    div.className = 'drug-card';
    div.onclick = () => openDrugModal(drug);
    
    div.innerHTML = `
        <div class="drug-card-header">
            <div>
                <div class="drug-name">${drug.name}</div>
                <div class="drug-generic">${drug.generic}</div>
            </div>
            <div class="evidence-level ${drug.evidenceLevel}">${drug.evidenceLevel}</div>
        </div>
        <div class="drug-description">${drug.description}</div>
        <div class="drug-genes">
            <h4>Associated Genes</h4>
            <div class="gene-tags">
                ${drug.genes.map(gene => <span class="gene-tag">${gene}</span>).join('')}
            </div>
        </div>
    `;
    
    return div;
}

function handleDrugDbSearch(e) {
    const query = e.target.value.toLowerCase();
    filterDrugDatabase();
}

function handleDrugDbFilter() {
    filterDrugDatabase();
}

function filterDrugDatabase() {
    const searchQuery = document.getElementById('drug-db-search').value.toLowerCase();
    const categoryFilter = document.getElementById('drug-category-filter').value;
    const evidenceFilter = document.getElementById('drug-evidence-filter').value;
    
    let filteredDrugs = DRUG_DATABASE;
    
    if (searchQuery) {
        filteredDrugs = filteredDrugs.filter(drug => 
            drug.name.toLowerCase().includes(searchQuery) ||
            drug.generic.toLowerCase().includes(searchQuery) ||
            drug.description.toLowerCase().includes(searchQuery)
        );
    }
    
    if (categoryFilter !== 'all') {
        filteredDrugs = filteredDrugs.filter(drug => drug.category === categoryFilter);
    }
    
    if (evidenceFilter !== 'all') {
        filteredDrugs = filteredDrugs.filter(drug => drug.evidenceLevel === evidenceFilter);
    }
    
    const container = document.getElementById('drug-database-grid');
    container.innerHTML = '';
    filteredDrugs.forEach(drug => {
        const drugCard = createDrugCard(drug);
        container.appendChild(drugCard);
    });
}

// Modal Functions
function openReportModal(reportId) {
    const report = typeof reportId === 'string' ? 
        AppState.reports.find(r => r.id === reportId) : reportId;
    
    if (!report) return;

    const modal = document.getElementById('report-modal');
    const title = document.getElementById('modal-report-title');
    const content = document.getElementById('modal-report-content');
    
    title.textContent = report.title;
    content.innerHTML = generateReportModalContent(report);
    
    modal.classList.add('active');
}

function generateReportModalContent(report) {
    return `
        <div class="report-details">
            <div class="detail-section">
                <h3>Patient Information</h3>
                <p><strong>Patient ID:</strong> ${report.patientId}</p>
                <p><strong>Patient Name:</strong> ${report.patientName}</p>
                <p><strong>Analysis Date:</strong> ${new Date(report.date).toLocaleString()}</p>
            </div>
            
            <div class="detail-section">
                <h3>Analysis Summary</h3>
                <p>${report.summary}</p>
                ${report.notes ? <p><strong>Notes:</strong> ${report.notes}</p> : ''}
            </div>
            
            <div class="detail-section">
                <h3>Analyzed Drugs</h3>
                <div class="drug-tags">
                    ${report.drugs.map(drug => <span class="gene-tag">${drug}</span>).join('')}
                </div>
            </div>
            
            <div class="detail-section">
                <h3>Analysis Statistics</h3>
                <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                    <div class="stat-item">
                        <strong>Total Variants:</strong> ${report.variants}
                    </div>
                    <div class="stat-item">
                        <strong>Drug Interactions:</strong> ${report.interactions}
                    </div>
                    <div class="stat-item">
                        <strong>High Risk:</strong> ${report.highRiskInteractions}
                    </div>
                    <div class="stat-item">
                        <strong>Status:</strong> ${report.status}
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>Configuration</h3>
                <ul>
                    <li>AI Analysis: ${report.config.useCohere ? 'Enabled' : 'Disabled'}</li>
                    <li>Detailed Analysis: ${report.config.detailedAnalysis ? 'Yes' : 'No'}</li>
                    <li>Alternative Drugs: ${report.config.includeAlternatives ? 'Yes' : 'No'}</li>
                    <li>References: ${report.config.includeReferences ? 'Yes' : 'No'}</li>
                </ul>
            </div>
        </div>
    `;
}

function openDrugModal(drug) {
    const modal = document.getElementById('drug-modal');
    const title = document.getElementById('modal-drug-title');
    const content = document.getElementById('modal-drug-content');
    
    title.textContent = drug.name;
    content.innerHTML = generateDrugModalContent(drug);
    
    modal.classList.add('active');
}

function generateDrugModalContent(drug) {
    return `
        <div class="drug-details">
            <div class="detail-section">
                <h3>Drug Information</h3>
                <p><strong>Brand Name:</strong> ${drug.name}</p>
                <p><strong>Generic Name:</strong> ${drug.generic}</p>
                <p><strong>Category:</strong> ${drug.category}</p>
                <p><strong>Evidence Level:</strong> <span class="evidence-level ${drug.evidenceLevel}">${drug.evidenceLevel}</span></p>
            </div>
            
            <div class="detail-section">
                <h3>Description</h3>
                <p>${drug.description}</p>
            </div>
            
            <div class="detail-section">
                <h3>Associated Pharmacogenes</h3>
                <div class="gene-tags">
                    ${drug.genes.map(gene => <span class="gene-tag">${gene}</span>).join('')}
                </div>
                <p style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                    These genes may affect how your body processes this medication.
                </p>
            </div>
            
            <div class="detail-section">
                <h3>Clinical Significance</h3>
                <p>Genetic variations in the associated genes may affect:</p>
                <ul>
                    <li>Drug metabolism and clearance</li>
                    <li>Therapeutic efficacy</li>
                    <li>Risk of adverse reactions</li>
                    <li>Optimal dosing requirements</li>
                </ul>
            </div>
        </div>
    `;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Settings Functions
function loadSettings() {
    const savedSettings = localStorage.getItem('pharmgenome-settings');
    if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        
        // Update form fields
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = settings[key];
                } else {
                    element.value = settings[key];
                }
            }
        });
        
        // Update app state
        if (settings['api-endpoint']) {
            AppState.apiEndpoint = settings['api-endpoint'];
        }
    }
}

function handleSettingsChange(e) {
    saveSettings();
}

function saveSettings() {
    const settings = {};
    
    // Collect all settings
    document.querySelectorAll('#settings input, #settings select').forEach(input => {
        if (input.type === 'checkbox') {
            settings[input.id] = input.checked;
        } else {
            settings[input.id] = input.value;
        }
    });
    
    localStorage.setItem('pharmgenome-settings', JSON.stringify(settings));
    showToast('Settings saved successfully', 'success');
}

async function testConnection() {
    try {
        showLoading();
        await apiCall('/health');
        showToast('Connection successful!', 'success');
    } catch (error) {
        showToast('Connection failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Data Management Functions
function loadStoredData() {
    const savedReports = localStorage.getItem('pharmgenome-reports');
    if (savedReports) {
        AppState.reports = JSON.parse(savedReports);
    }
}

function saveReports() {
    localStorage.setItem('pharmgenome-reports', JSON.stringify(AppState.reports));
}

function exportData() {
    const data = {
        reports: AppState.reports,
        exportDate: new Date().toISOString(),
        version: '1.0'
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = pharmgenome-export-${new Date().toISOString().split('T')[0]}.json;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Data exported successfully', 'success');
}

function exportAllData() {
    exportData();
}

function clearAllData() {
    if (confirm('Are you sure you want to clear all data? This action cannot be undone.')) {
        AppState.reports = [];
        localStorage.removeItem('pharmgenome-reports');
        updateDashboard();
        loadReports();
        showToast('All data cleared successfully', 'success');
    }
}

async function downloadReport(reportId) {
    try {
        const report = AppState.reports.find(r => r.id === reportId);
        if (!report || !report.jobId) {
            showToast('Report not available for download', 'error');
            return;
        }
        
        // Create download link
        const downloadUrl = ${AppState.apiEndpoint}/api/report/${report.jobId}/download;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = pharmacogenomics_report_${reportId}.html;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast('Report download started', 'success');
    } catch (error) {
        console.error('Download failed:', error);
        showToast('Download failed', 'error');
    }
}

async function viewFullReport(jobId) {
    try {
        // Open the full HTML report in a new window
        const reportUrl = ${AppState.apiEndpoint}/api/report/${jobId}/view;
        const newWindow = window.open(reportUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
        
        if (!newWindow) {
            showToast('Please allow popups to view the full report', 'warning');
        } else {
            showToast('Opening full report in new window', 'success');
        }
    } catch (error) {
        console.error('Failed to open full report:', error);
        showToast('Failed to open full report', 'error');
    }
}

// Utility Functions
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = toast ${type};
    
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

// Initialize drug selection when page loads
document.addEventListener('DOMContentLoaded', function() {
    populateAvailableDrugs();
    updateSelectedDrugs();
});
