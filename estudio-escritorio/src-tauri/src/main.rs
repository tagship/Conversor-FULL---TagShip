// Estudio para Windows: una ventana propia que abre el Estudio (https://tagshipstudio.web.app).
// Como carga la app desde internet, se actualiza sola cada vez que se publica una versión nueva.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("no se pudo abrir el Estudio");
}
