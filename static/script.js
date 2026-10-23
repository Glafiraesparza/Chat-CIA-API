
// ELEMENTOS DE LA INTERFAZ
const usuarioSelect = document.getElementById("usuario");
const contacto = document.getElementById("contacto");
const contenedor = document.getElementById("mensajes");
const formulario = document.getElementById("formulario");
const textoInput = document.getElementById("texto");

let cargaActual = 0;

// Identificar remitente y destinatario
function usuariosActuales() {
    const usuario = Number(usuarioSelect.value);

    return {
        usuario,
        destinatario: usuario === 1 ? 2 : 1
    };
}

// Realizar peticiones HTTP a FastAPI
async function solicitar(url, opciones = {}) {
    const respuesta = await fetch(url, opciones);

    if (!respuesta.ok) {
        throw new Error(`Error HTTP ${respuesta.status}`);
    }

    return respuesta.json();
}

// CONSULTAR Y MOSTRAR LOS MENSAJES
async function cargarMensajes() {
    const carga = ++cargaActual;
    const { usuario, destinatario } = usuariosActuales();

    contacto.textContent =
        destinatario === 1 ? "Chat con Alice" : "Chat con Bob";

    // PASO 4: Consultar los mensajes desde SQLite
    const mensajes = await solicitar(
        `/mensajes?usuario_id=${usuario}&contacto_id=${destinatario}`
    );

    if (carga !== cargaActual) return;

    contenedor.replaceChildren();

    // Mostrar inicialmente "No verificado"
    const elementos = mensajes.map((mensaje) => {
        const burbuja = document.createElement("div");

        burbuja.className = "mensaje " +
            (mensaje.remitente_id === usuario ? "propio" : "recibido");

        const contenido = document.createElement("p");
        contenido.textContent = "Descifrando mensaje...";

        const estado = document.createElement("span");
        estado.className = "estado";
        estado.textContent = "No verificado";

        burbuja.append(contenido, estado);
        contenedor.appendChild(burbuja);

        return { mensaje, contenido, estado };
    });

    // PASO 5: DESCIFRAR LOS MENSAJES
    for (const elemento of elementos) {
        if (carga !== cargaActual) return;

        const { mensaje, contenido, estado } = elemento;

        try {
            const resultado = await solicitar(
                `/mensajes/${mensaje.id}/descifrar`,
                { method: "POST" }
            );

            if (carga !== cargaActual) return;

            // Mostrar el texto descifrado
            contenido.textContent = resultado.texto;

            // PASO 6: VERIFICAR LA INTEGRIDAD
            const verificacion = await solicitar(
                `/mensajes/${mensaje.id}/verificar`,
                { method: "POST" }
            );

            if (carga !== cargaActual) return;

            if (verificacion.valid === true) {
                estado.textContent = "Mensaje verificado";
                estado.classList.add("verificado");
            } else {
                estado.textContent = "Integridad comprometida";
                estado.classList.add("invalido");
            }

        } catch (error) {
            if (carga !== cargaActual) return;

            contenido.textContent = "No se pudo procesar el mensaje";
            estado.textContent = "No verificado";
            console.error(error);
        }
    }

    if (carga === cargaActual) {
        contenedor.scrollTop = contenedor.scrollHeight;
    }
}

// ENVIAR MENSAJES
formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const mensaje = textoInput.value.trim();
    if (!mensaje) return;

    const { usuario, destinatario } = usuariosActuales();
    const boton = formulario.querySelector("button");

    boton.disabled = true;

    try {
        // PASOS 1, 2 Y 3:
        // Enviar al backend para cifrar, firmar y guardar en SQLite
        await solicitar("/mensajes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                remitente_id: usuario,
                destinatario_id: destinatario,
                mensaje: mensaje
            })
        });

        textoInput.value = "";

        // Consultar nuevamente los mensajes desde SQLite
        await cargarMensajes();

    } catch (error) {
        alert("No se pudo enviar el mensaje");
        console.error(error);
    } finally {
        boton.disabled = false;
    }
});

// CAMBIAR ENTRE ALICE Y BOB
usuarioSelect.addEventListener("change", () => {
    cargarMensajes().catch(console.error);
});

// CARGAR LOS MENSAJES AL ABRIR EL CHAT
cargarMensajes().catch(console.error);
