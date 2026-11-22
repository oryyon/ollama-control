# Ollama Control: Specificatie Pentru Rescriere In Tauri + Rust

## Context tinta

Acest document centralizeaza informatiile necesare pentru a recrea proiectul Ollama Control intr-o implementare noua, bazata pe Tauri + Rust.

Mediul tinta cerut pentru noul proiect:

- OS: Kubuntu 24.04
- CPU: Intel i3-5005U
- RAM: 12 GB
- Flux de dezvoltare: VS Code + Continue
- Model local de asistenta: Ollama cu `qwen2.5-coder:7b`

Obiectivul functional al noii versiuni este sa pastreze comportamentul aplicatiei curente, dar cu arhitectura desktop moderna, backend Rust si frontend Tauri.

## Ce este Ollama Control in proiectul actual

Aplicatia existenta este un desktop app Python construit cu CustomTkinter pentru administrarea unei instante locale Ollama.

Functiile principale actuale:

- pornire, oprire si restart pentru serviciul `ollama` prin `systemd`;
- afisare stare serviciu, substate si uptime;
- afisare versiune client Ollama;
- detectare model activ;
- monitorizare consum RAM si, daca exista GPU NVIDIA, VRAM;
- incarcare model Ollama cu confirmare reala din backend;
- eject model activ;
- creare modele derivate cu `PARAMETER num_ctx`;
- stergere modele Ollama;
- setari persistente pentru tema, auto-refresh, confirmare stop/restart si `keepalive`;
- jurnal local in `~/.ollama_control_ui/app.log`.

## Arhitectura curenta

### Punct de intrare

Aplicatia porneste din `ollama_control.py`.

Fluxul de bootstrap actual:

1. initializeaza CustomTkinter;
2. incarca setarile din `settings.json`;
3. aplica tema si intervalul de auto-refresh;
4. construieste fereastra principala;
5. leaga callback-ul pentru modelul activ;
6. lanseaza primul refresh de stare;
7. programeaza refresh-ul periodic.

### Module relevante

- `config/settings.py`: setari, persistenta JSON, tema, auto-refresh;
- `core/app_state.py`: stare UI in memorie;
- `core/commands.py`: executie `pkexec systemctl` pentru start/stop/restart;
- `core/state_manager.py`: orchestrare refresh UI si task-uri in background;
- `core/ollama_models.py`: lista modele Ollama, stergere, cache;
- `core/model_config.py`: creare modele derivate cu `num_ctx`;
- `services/systemd_service.py`: citire stare `systemd`;
- `services/ollama_info.py`: versiune Ollama, model activ, normalizare nume;
- `services/resource_monitor.py`: RAM/VRAM si uptime;
- `ui/main_window.py`: dashboard principal;
- `ui/model_window.py`: fereastra de administrare modele;
- `ui/settings_window.py`: setari aplicatie;
- `utils/logging_config.py`: logging in fisier si in stdout.

## Comportamente critice care trebuie pastrate

### 1. Control serviciu Ollama

Aplicatia trebuie sa poata rula:

- `systemctl is-active ollama`
- `systemctl show ollama --property=SubState --value`
- `systemctl show ollama --property=ActiveEnterTimestamp --value`
- `pkexec systemctl start ollama`
- `pkexec systemctl stop ollama`
- `pkexec systemctl start ollama` dupa stop, pentru restart

Cerintele UX actuale:

- comenzile nu blocheaza UI-ul;
- butoanele devin disabled pe durata executiei;
- pentru `stop` si `restart` exista confirmare optionala;
- utilizatorul primeste notificari de succes, warning sau eroare;
- dupa comanda se forteaza un refresh al starii serviciului.

### 2. Detectarea modelului activ

Logica actuala:

1. daca serviciul nu este `active`, modelul este considerat indisponibil;
2. se incearca `ollama ps`;
3. daca nu rezulta clar un model, se face fallback pe scanarea proceselor `ps -eo args=` si identificarea `ollama runner`;
4. numele este normalizat prin eliminarea sufixului `:latest`.

Stari text importante folosite in UI:

- `Se verifică...`
- `Indisponibil`
- `niciun model încărcat`
- `runner detectat`

Noua versiune ar trebui sa mentina acelasi sens functional, chiar daca textele exacte pot fi rafinate.

### 3. Incarcarea unui model Ollama

Flux actual:

1. utilizatorul selecteaza un model din lista Ollama;
2. aplicatia ruleaza comanda non-interactiva:

```bash
ollama run MODEL "" --keepalive DURATA
```

3. dupa terminarea comenzii, aplicatia asteapta confirmarea reala ca modelul a devenit activ;
4. daca activarea apare in intervalul admis, operatia este marcata cu succes;
5. daca nu, utilizatorul vede eroare de timeout sau eroare de proces.

Detalii de timp curente:

- timeout de baza pentru confirmare: `90s`;
- fereastra suplimentara dupa iesirea procesului: `20s`;
- timeoutul poate creste in functie de dimensiunea modelului: `max(size_gb * 8, 90s)`.

Acesta este un comportament important si trebuie pastrat in backend-ul Rust, fiind mai robust decat marcarea succesului imediat dupa `ollama run`.

### 4. Eject model activ

Flux actual:

1. detecteaza modelul activ;
2. ruleaza `ollama stop MODEL`;
3. repeta verificarea modelului activ pentru cateva secunde;
4. daca modelul nu mai este activ, marcheaza eject-ul ca reusit.

### 5. Creare model derivat cu context custom

Flux actual:

1. utilizatorul alege un model Ollama;
2. selecteaza `num_ctx` dintr-un set de optiuni;
3. aplicatia genereaza un model derivat cu nume de forma:

```text
BASE_NAME-ctxNUMAR
```

4. Modelfile-ul temporar contine:

```text
FROM BASE_NAME
PARAMETER num_ctx NUMAR
```

5. se ruleaza `ollama create` si se reimprospateaza lista.

Optiuni actuale pentru `num_ctx`:

- 2048
- 4096
- 8192
- 16384
- 32768
- 65536
- 128000

### 6. Stergere model Ollama

Flux actual:

1. confirmare explicita in UI;
2. comanda `ollama rm MODEL`;
3. invalidare cache;
4. refresh lista.

### 7. Monitorizare resurse

Flux actual:

- RAM: scanare procese `ps -eo pid,rss,comm,args=` si insumare pentru procese ce contin `ollama`;
- VRAM: optional, prin `nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits` si corelare PIDs cu procese Ollama;
- daca nu se gasesc valori, UI-ul afiseaza `—`.

### 8. Persistenta setarilor

Fisier actual: `settings.json` in radacina aplicatiei sau langa executabilul impachetat.

Schema curenta:

```json
{
  "auto_refresh_interval": 5,
  "confirm_before_stop": true,
  "theme": "dark",
  "ollama_keepalive": "10m",
  "recent_models": [],
  "model_contexts": {}
}
```

Semnificatia campurilor:

- `auto_refresh_interval`: secunde; `0` inseamna dezactivat;
- `confirm_before_stop`: confirma `stop` si `restart`;
- `theme`: `dark` sau `light`;
- `ollama_keepalive`: valori precum `45s`, `10m`, `2h`, `1d`;
- `recent_models`: ultimele modele activate;
- `model_contexts`: mapare model -> ultimul `num_ctx` folosit.

## UI-ul actual

### Fereastra principala

Contine:

- card de status serviciu;
- uptime;
- badge ONLINE / OFFLINE / ERROR / CHECKING / UNKNOWN;
- model activ;
- versiune Ollama;
- resurse RAM/VRAM;
- buton `Încarcă Model`;
- buton `Eject Model`;
- buton `Setări`;
- buton `Log`;
- butoane `Pornește`, `Restart`, `Reîmprospătează`, `Oprește`;
- notificari in partea de jos sau intr-o zona dedicata.

### Fereastra Model Loader

Afiseaza exclusiv modelele disponibile in Ollama.

Elemente functionale:

- search/filter dupa nume;
- lista scrollabila;
- coloane: `Stare`, `Model`, `Dimensiune`, `Parametri`;
- indicator vizual pentru modelul activ;
- actiuni pe rand:
  - `Select` pentru incarcarea modelului;
  - `⚙️` pentru configurarea modelelor Ollama;
  - `🗑️` pentru stergerea modelelor Ollama;
- progres vizual pentru activare;
- inchidere sigura a ferestrei dupa succes sau anulare.

### Fereastra Setari

Optiuni expuse:

- auto-refresh: `Off`, `2 sec`, `5 sec`, `10 sec`, `30 sec`;
- confirmare inainte de Stop/Restart;
- `keepalive` preset sau custom;
- comutare tema light/dark;
- afisare modele recente.

## Dependinte externe si ipoteze de runtime

Noua implementare trebuie sa presupuna explicit:

- `ollama` instalat si disponibil in `PATH`;
- serviciu `ollama` gestionat de `systemd`;
- `pkexec` disponibil pentru operatiile privilegiate;
- `curl` disponibil daca se pastreaza verificarea rapida a serverului;
- optional `nvidia-smi` pentru VRAM.

## Cerinte non-functionale pentru Tauri + Rust

Avand in vedere hardware-ul tinta, noua implementare ar trebui sa prioritizeze:

- consum redus de RAM;
- pornire rapida;
- operatii async fara blocarea UI-ului;
- intervale de polling conservative;
- cache local pentru lista de modele Ollama;
- logging clar pentru diagnostic.

Pentru i3-5005U cu 12 GB RAM:

- evita polling agresiv sub 2 secunde;
- evita scanari costisitoare continue cand serviciul Ollama este oprit;
- ruleaza procesele externe prin task-uri asincrone sau thread pool dedicat;
- serializeaza comenzile critice de service pentru a evita concurenta.

## Recomandare finala de frontend stack

Pentru mediul tinta specificat, recomandarea finala pentru frontend este:

- Tauri
- Vanilla TypeScript
- Vite
- CSS simplu

Aceasta combinatie este preferata pentru acest proiect din trei motive practice:

- reduce complexitatea pe care trebuie sa o gestioneze un model local de 7B;
- mentine frontend-ul usor de construit si reparat incremental pe hardware modest;
- evita straturi suplimentare de abstractie care nu sunt necesare pentru un utility app desktop de tip dashboard.

Ce inseamna concret aceasta recomandare:

- fara framework frontend mare in prima versiune;
- fara librarie de state management dedicata in prima versiune;
- fara component libraries grele;
- componente UI mici, scrise manual;
- CSS organizat simplu, cu variabile pentru culori, spacing si stari.

De ce nu React ca recomandare principala:

- adauga mai mult boilerplate si mai multe conventii pentru un proiect relativ mic;
- creste suprafata de eroare pentru un model local precum `qwen2.5-coder-7b-instruct`;
- nu aduce un avantaj suficient de mare pentru un dashboard desktop utilitar precum Ollama Control.

De ce nu Svelte sau Vue ca alegere implicita:

- ambele pot functiona bine tehnic;
- totusi, pentru acest caz, Vanilla TypeScript ramane mai previzibil pentru generare incrementala, debug si mentenanta asistata de model;
- sintaxa si conventiile suplimentare ale unui framework cresc costul cognitiv fara un castig esential in prima iteratie.

Concluzie practica pentru implementare:

- backend: Rust in Tauri;
- frontend: Vite + Vanilla TypeScript;
- stilizare: CSS simplu, preferabil modularizat pe ecrane sau componente.

## Recomandare de arhitectura Tauri + Rust

### Backend Rust

Responsabilitati recomandate:

- executie comenzi shell si `systemctl`;
- parsare output `ollama`, `ps`, `nvidia-smi`;
- gestionare refresh si cache;
- persistenta setari;
- logging;
- emitere evenimente catre frontend.

Module Rust recomandate:

- `src-tauri/src/main.rs`: bootstrap Tauri;
- `src-tauri/src/commands/service.rs`: start/stop/restart/status;
- `src-tauri/src/commands/models.rs`: listare, activare, eject, delete;
- `src-tauri/src/commands/settings.rs`: load/save settings;
- `src-tauri/src/monitoring/resources.rs`: RAM/VRAM;
- `src-tauri/src/monitoring/ollama.rs`: versiune, model activ;
- `src-tauri/src/state.rs`: stare partajata si lock-uri;
- `src-tauri/src/logging.rs`: configurare jurnal.

Crates utile:

- `tauri`
- `serde`
- `serde_json`
- `tokio`
- `anyhow`
- `thiserror`
- `tracing`
- `tracing-subscriber`
- `dirs`
- `chrono`
- `sysinfo`
- optional `regex`

### Frontend Tauri

Frontend-ul Tauri recomandat pentru acest proiect este bazat pe Vanilla TypeScript peste Vite, fara framework UI major in prima versiune.

Frontend-ul trebuie sa aiba cel putin aceste view-model-uri:

- service status;
- metadata Ollama;
- model loader state;
- settings state;
- notifications queue.

Componente recomandate:

- `MainDashboard`
- `StatusCard`
- `MetaCard`
- `ActionBar`
- `ModelLoaderModal`
- `ModelTable`
- `SettingsModal`
- `NotificationStack`

Organizare recomandata pentru frontend:

- `src/main.ts` pentru bootstrap UI;
- `src/styles/` pentru CSS global si CSS pe zone functionale;
- `src/components/` pentru componente UI mici;
- `src/state/` pentru stare UI locala si helperi de polling;
- `src/api/` pentru invocari Tauri si mapare de raspunsuri.

## Contract minim de API intre frontend si backend

Exemple de comenzi Tauri utile:

- `get_service_status() -> ServiceStatus`
- `start_ollama_service() -> CommandResult`
- `stop_ollama_service() -> CommandResult`
- `restart_ollama_service() -> CommandResult`
- `get_ollama_version() -> String`
- `get_active_model() -> ActiveModelState`
- `get_resource_usage() -> ResourceUsage`
- `list_ollama_models(force_refresh: bool) -> Vec<ModelEntry>`
- `run_ollama_model(name: String) -> CommandResult`
- `eject_active_model() -> CommandResult`
- `create_model_with_context(base_name: String, num_ctx: u32) -> CommandResult`
- `delete_ollama_model(name: String) -> CommandResult`
- `load_settings() -> AppSettings`
- `save_settings(settings: AppSettings) -> CommandResult`
- `open_log_file() -> CommandResult`

Structuri de date recomandate:

- `ServiceStatus { active_state, sub_state, active_timestamp, uptime_text }`
- `ModelEntry { name, path, size, params, is_active }`
- `ResourceUsage { ram_mb, vram_mb, display_text }`
- `AppSettings { auto_refresh_interval, confirm_before_stop, theme, ollama_keepalive, recent_models, model_contexts }`
- `CommandResult { success, message }`

## Comportamente de refresh care merita replicate

Strategia actuala este buna si ar trebui mentinuta conceptual:

- refresh serviciu mai rar decat restul UI-ului;
- versiunea Ollama nu este recitita la fiecare refresh;
- resursele nu sunt recitite cand serviciul este oprit;
- modelul activ si lista de modele sunt normalizate si deduplicate;
- mesajele repetitive din log sunt reduse.

Valori actuale:

- auto-refresh configurabil din UI;
- refresh status serviciu: minim 15 secunde sau de 3 ori intervalul global;
- refresh versiune: 60 secunde;
- refresh resurse: 20 secunde.

## Logging si fisiere locale

Fisier de log actual:

- `~/.ollama_control_ui/app.log`

Recomandare pentru noul proiect:

- pastreaza aceeasi locatie sau o locatie predictibila compatibila XDG;
- logheaza atat in fisier, cat si in consola de dezvoltare;
- include output relevant pentru comenzi `ollama`, `systemctl` si erori de parsare.

## Elemente care pot fi imbunatatite in rescriere

Rescrierea in Tauri + Rust poate imbunatati proiectul fara a-i schimba scopul:

- inlocuire thread-uri ad-hoc cu task-uri `tokio` bine delimitate;
- API intern tipizat pentru toate starile si erorile;
- event bus clar intre backend si frontend;
- testare mai usoara pentru parsare de output CLI;
- packaging Linux mai curat fata de distributia PyInstaller;
- posibilitate viitoare de a inlocui o parte din parsingul CLI cu API-ul HTTP Ollama unde este mai robust.

## Cerinte de compatibilitate functionala

Versiunea noua ar trebui sa livreze minim paritatea de mai jos:

1. dashboard cu stare serviciu, model activ, versiune si resurse;
2. start/stop/restart cu elevare prin `pkexec`;
3. listare modele Ollama;
4. selectare si confirmare reala a modelului activ;
5. eject model;
6. stergere model;
7. creare model derivat cu `num_ctx`;
8. setari persistente;
9. deschidere log din UI;
10. notificari clare pentru operatii si erori.

## Ordine recomandata de implementare pentru noul proiect

1. bootstrap Tauri + sistem de logging + persistenta setari;
2. comenzi Rust pentru status serviciu si versiune Ollama;
3. dashboard principal cu refresh controlat;
4. listare modele Ollama si detectare model activ;
5. `run model` cu confirmare de activare;
6. eject model;
7. creare model derivat cu `num_ctx`;
8. monitorizare RAM/VRAM;
9. polish UI, teme si packaging Linux.

## Rezumat practic

Pe scurt, Ollama Control este un panou desktop Linux pentru Ollama, concentrat pe patru lucruri:

- controlul serviciului `ollama`;
- vizibilitate asupra starii reale a backend-ului;
- administrarea modelelor Ollama;
- activarea rapida a modelelor deja instalate in Ollama.

Daca noul proiect Tauri + Rust pastreaza aceste fluxuri si aceste garantii de confirmare, va reproduce fidel aplicatia actuala intr-o forma mai moderna si mai potrivita pentru mediul hardware si de dezvoltare specificat.