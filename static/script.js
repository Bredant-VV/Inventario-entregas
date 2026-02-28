async function cargarRegistros() {
    const res = await fetch("/api/registros");
    const data = await res.json();

    const container = document.getElementById("cards-container");
    container.innerHTML = "";

    data.forEach(r => {
        container.innerHTML += `
        <div class="card">
            <h3>${r.id}</h3>
            <p><b>Accesorio:</b> ${r.accesorio}</p>
            <p><b>Modelo:</b> ${r.modelo}</p>
            <p><b>Nombre:</b> ${r.nombre}</p>
            <p><b>POO:</b> ${r.poo}</p>
            <p><b>Factura:</b> ${r.factura}</p>
            <button onclick="marcarEntregado('${r.id}')">Entregado</button>
            <button onclick="eliminarRegistro('${r.id}')">Eliminar</button>
        </div>
        `;
    });
}

async function agregarRegistro() {
    const nuevo = {
        id: id.value,
        accesorio: accesorio.value,
        modelo: modelo.value,
        nombre: nombre.value,
        poo: poo.value,
        factura: factura.value,
        entregado: "No"
    };

    await fetch("/api/agregar", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(nuevo)
    });

    cargarRegistros();
}

async function eliminarRegistro(id) {
    await fetch(`/api/eliminar/${id}`, { method: "DELETE" });
    cargarRegistros();
}

async function marcarEntregado(id) {
    await fetch(`/api/entregado/${id}`, { method: "PUT" });
    cargarRegistros();
}

cargarRegistros();