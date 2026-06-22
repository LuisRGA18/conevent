let memberCount = 1;

// Control del cambio de pasos
function nextStep(stepNumber) {
    // Validación básica nativa de inputs del paso 1 antes de avanzar
    const titulo = document.getElementById('titulo_proyecto');
    const carrera = document.getElementById('carrera_proyecto');
    const grupo = document.getElementById('grupo_proyecto');
    const descripcion = document.getElementById('descripcion_proyecto');

    if (!titulo.checkValidity() || !carrera.checkValidity() || !grupo.checkValidity() || !descripcion.checkValidity()) {
        alert("Por favor, rellena todos los campos obligatorios antes de continuar.");
        return;
    }

    // Cambiar visibilidad de pestañas
    document.getElementById('wizard-step-1').classList.remove('active');
    document.getElementById('wizard-step-2').classList.add('active');

    // Cambiar estado visual del Stepper
    document.getElementById('step-indicator-1').classList.add('completed');
    document.getElementById('step-indicator-2').classList.add('active');
}

function prevStep(stepNumber) {
    document.getElementById('wizard-step-2').classList.remove('active');
    document.getElementById('wizard-step-1').classList.add('active');

    document.getElementById('step-indicator-1').classList.remove('completed');
    document.getElementById('step-indicator-2').classList.remove('active');
}

// Vista previa dinámica del Logotipo cargado
document.getElementById('logo_empresa').addEventListener('change', function(event) {
    const [file] = this.files;
    if (file) {
        const previewImg = document.getElementById('logo-preview');
        const container = document.getElementById('preview-container');
        previewImg.src = URL.createObjectURL(file);
        container.classList.remove('preview-hidden');
    }
});

// Agregar integrantes dinámicamente
document.getElementById('btn-agregar-integrante').addEventListener('click', function() {
    memberCount++;
    const contenedor = document.getElementById('contenedor-integrantes');
    
    const nuevaFila = document.createElement('div');
    nuevaFila.classList.add('integrante-row');
    nuevaFila.id = `integrante-${memberCount}`;
    
    nuevaFila.innerHTML = `
        <div class="row-header">
            <span>Integrante ${memberCount}</span>
            <button type="button" class="btn-remove-member" onclick="removeMember(${memberCount})">Eliminar miembro</button>
        </div>
        <div class="integrante-grid">
            <div class="form-group">
                <label>Matrícula / Correo *</label>
                <input type="text" name="matricula[]" placeholder="Ej. 2023123456" required>
            </div>
            <div class="form-group">
                <label>Nombre(s) *</label>
                <input type="text" name="nombres[]" placeholder="Ej. Juan Carlos" required>
            </div>
            <div class="form-group">
                <label>Apellidos *</label>
                <input type="text" name="apellidos[]" placeholder="Ej. Pérez Pérez" required>
            </div>
        </div>
    `;
    
    contenedor.appendChild(nuevaFila);
});

// Eliminar un integrante de la lista
function removeMember(id) {
    const fila = document.getElementById(`integrante-${id}`);
    if (fila) {
        fila.remove();
        // Nota: No reiniciamos el contador estricto para evitar conflictos de IDs, 
        // los arreglos 'name="matricula[]"' se empaquetan solos correctamente al enviarse a Django.
    }
}