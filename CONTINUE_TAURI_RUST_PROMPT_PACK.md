# Set Complet De Prompturi Pentru Continue: Rescrierea Ollama Control In Tauri + Rust

## Cum se foloseste acest fisier

Aceste prompturi sunt scrise pentru:

- VS Code + Continue
- LM Studio
- `qwen2.5-coder-7b-instruct`
- Linux desktop
- rescrierea proiectului Ollama Control in Tauri + Rust

Fiecare prompt este gandit pentru lucru incremental. Nu rula multe prompturi deodata. Foloseste unul, valideaza rezultatul, apoi treci la urmatorul.

Regula de folosire:

1. copiaza un singur prompt;
2. lasa modelul sa implementeze;
3. ruleaza build sau test;
4. daca apare eroare, foloseste prompturile de reparatie de la final;
5. continua doar dupa validare.

## Context scurt reutilizabil

Poti prefixa multe sesiuni cu acest context scurt:

```text
Lucrezi la rescrierea proiectului Ollama Control in Tauri + Rust.
Respecta specificatia din TAURI_RUST_REBUILD_SPEC.md.
Aplicatia tinta ruleaza pe Linux si foloseste systemd, pkexec, ollama CLI si optional nvidia-smi.
Frontend-ul tinta este: Vanilla TypeScript + Vite + CSS simplu.
Solutia trebuie sa fie simpla, robusta si potrivita pentru hardware modest.
Modifica minimul necesar si nu inventa fisiere sau API-uri inexistente.
```

## Faza 1: Bootstrap proiect

### Prompt 1.1: creare schelet Tauri

```text
Context:
Lucrezi la rescrierea proiectului Ollama Control in Tauri + Rust.
Respecta specificatia din TAURI_RUST_REBUILD_SPEC.md.

Task:
Creeaza structura initiala a proiectului Tauri pentru aplicatia Ollama Control.

Constraints:
- Tinta este Linux desktop.
- Frontend-ul trebuie pregatit explicit pentru Vanilla TypeScript + Vite + CSS simplu.
- Pastreaza setup-ul simplu.
- Nu adauga librarii inutile.
- Pregateste structura astfel incat backend-ul Rust si frontend-ul sa poata evolua incremental.

Output:
- Creeaza fisierele initiale necesare.
- Explica pe scurt structura propusa.
- Nu implementa inca fluxurile de business.
```

### Prompt 1.2: definire module backend

```text
Context:
Lucrezi in proiectul Tauri nou creat pentru Ollama Control.

Task:
Organizeaza backend-ul Rust in module clare pentru:
- service status
- modele Ollama
- LM Studio
- setari
- monitorizare resurse
- logging
- stare partajata

Constraints:
- Nu implementa inca logica completa.
- Creeaza doar structura si wiring-ul minim.
- Pastreaza modulele usor de extins.

Output:
- Scrie codul si module declarations necesare.
- Explica scurt de ce structura este potrivita.
```

### Prompt 1.3: configurare logging

```text
Task:
Configureaza logging-ul pentru backend-ul Rust astfel incat aplicatia sa scrie atat in consola, cat si intr-un fisier local predictibil.

Constraints:
- Locatia logului trebuie sa fie compatibila Linux.
- Mesajele trebuie sa fie utile pentru diagnosticarea comenzilor systemd si ollama.
- Nu complica setup-ul.

Output:
- Cod complet.
- Explica locatia logului si initializarea.
```

## Faza 2: tipuri si contracte de date

### Prompt 2.1: structuri partajate

```text
Context:
Respecta TAURI_RUST_REBUILD_SPEC.md.

Task:
Defineste structurile serializabile folosite intre backend si frontend:
- ServiceStatus
- ModelEntry
- ActiveModelState
- ResourceUsage
- AppSettings
- CommandResult

Constraints:
- Foloseste serde.
- Pastreaza campurile simple si explicite.
- Nu include logica de business in aceste structuri.

Output:
- Cod complet intr-un modul dedicat.
- Explica pe scurt rolul fiecarui tip.
```

### Prompt 2.2: valori implicite pentru setari

```text
Task:
Implementeaza structura `AppSettings` cu valori implicite echivalente cu proiectul Python:
- auto_refresh_interval = 5
- confirm_before_stop = true
- theme = "dark"
- ollama_keepalive = "10m"
- recent_models = []
- model_contexts = {}

Constraints:
- Pastreaza structura usor serializabila in JSON.
- Nu implementa inca UI pentru setari.

Output:
- Cod complet.
- Include metoda sau implementarea pentru valori implicite.
```

## Faza 3: persistenta setari

### Prompt 3.1: load/save settings JSON

```text
Context:
Aplicatia Tauri trebuie sa pastreze setari similare cu proiectul Python.

Task:
Implementeaza functiile Rust pentru:
- incarcarea setarilor din JSON
- salvarea setarilor in JSON
- fallback la default daca fisierul lipseste sau este invalid

Constraints:
- Pastreaza formatul simplu.
- Gestioneaza erorile fara panic.
- Foloseste o locatie predictibila pentru fisierul de setari.

Output:
- Cod complet.
- Explica ce se intampla in caz de fisier corupt.
```

### Prompt 3.2: comenzi Tauri pentru setari

```text
Task:
Expune prin Tauri doua comenzi:
- load_settings()
- save_settings(settings)

Constraints:
- Returneaza raspunsuri serializabile.
- Nu dubla logica daca exista deja functii helper.
- Modifica minimul necesar.

Output:
- Cod complet.
- Arata cum sunt inregistrate comenzile.
```

## Faza 4: service status systemd

### Prompt 4.1: citire stare serviciu

```text
Context:
Aplicatia trebuie sa citeasca starea serviciului `ollama` din systemd.

Task:
Implementeaza functia Rust care ruleaza:
- `systemctl is-active ollama`
- `systemctl show ollama --property=SubState --value`
- `systemctl show ollama --property=ActiveEnterTimestamp --value`

Constraints:
- Returneaza `ServiceStatus`.
- Nu bloca inutil thread-ul principal.
- In caz de eroare, intoarce o stare sigura si predictibila.

Output:
- Cod complet.
- Explica fallback-ul folosit.
```

### Prompt 4.2: formatare uptime

```text
Task:
Scrie o functie Rust care transforma `ActiveEnterTimestamp` intr-un text de forma:
- `Activ de 3m`
- `Activ de 2h 14m`
- `Activ de 1z 4h`

Constraints:
- Daca timestamp-ul lipseste sau nu poate fi parsat, returneaza `Uptime indisponibil`.
- Functia trebuie sa fie pura si usor de testat.

Output:
- Cod complet.
- Include teste unitare pentru cel putin 3 cazuri.
```

### Prompt 4.3: comenzi start/stop/restart

```text
Context:
Aplicatia trebuie sa controleze serviciul `ollama` cu elevare prin pkexec.

Task:
Implementeaza comenzile Tauri:
- start_ollama_service()
- stop_ollama_service()
- restart_ollama_service()

Constraints:
- Foloseste `pkexec systemctl`.
- Returneaza `CommandResult`.
- Captureaza stdout si stderr utile.
- Nu implementa inca partea de frontend.

Output:
- Cod complet.
- Explica cum este tratat cazul de anulare sau lipsa autorizarii.
```

## Faza 5: versiune Ollama si model activ

### Prompt 5.1: versiune Ollama

```text
Task:
Implementeaza functia Rust care ruleaza `ollama --version` si extrage un text de versiune util pentru UI.

Constraints:
- Gestioneaza stdout si stderr.
- Daca versiunea nu poate fi detectata, returneaza un text explicit de indisponibilitate.
- Nu adauga caching in acest pas.

Output:
- Cod complet.
- Include 2 teste unitare pentru parsarea output-ului.
```

### Prompt 5.2: detectare model activ

```text
Context:
Respecta logica din proiectul Python pentru modelul activ.

Task:
Implementeaza detectarea modelului activ astfel:
1. daca serviciul nu este active, modelul este indisponibil;
2. incearca `ollama ps`;
3. daca nu rezulta clar un model, foloseste fallback pe scanarea proceselor;
4. normalizeaza sufixul `:latest`.

Constraints:
- Returneaza o structura clara, nu un simplu string brut.
- Trateaza explicit cazurile `niciun model încărcat`, `indisponibil` si fallback runner.
- Codul trebuie sa fie robust la output partial.

Output:
- Cod complet.
- Include teste pentru parser unde este fezabil.
```

### Prompt 5.3: helper de normalizare nume model

```text
Task:
Scrie un helper Rust care normalizeaza numele unui model Ollama prin eliminarea sufixului `:latest` si a spatiilor inutile.

Constraints:
- Functie pura.
- Usor de testat.

Output:
- Cod complet.
- Include teste unitare.
```

## Faza 6: listare modele Ollama

### Prompt 6.1: parsare `ollama list`

```text
Task:
Scrie o functie Rust care parseaza output-ul comenzii `ollama list` intr-un `Vec<ModelEntry>`.

Constraints:
- Fii tolerant la spatii multiple.
- Extrage cel putin `name`, `size` si `params`.
- Daca output-ul este gol sau invalid, returneaza lista goala.

Output:
- Cod complet.
- Include teste unitare pentru header valid, input gol si spacing neregulat.
```

### Prompt 6.2: executie reala `ollama list`

```text
Task:
Implementeaza functia care ruleaza `ollama list`, parseaza rezultatul si returneaza lista de modele Ollama.

Constraints:
- Daca serverul nu raspunde, returneaza un rezultat clar pentru frontend.
- Nu bloca UI-ul.
- Nu implementa inca cache.

Output:
- Cod complet.
- Explica cum este semnalata indisponibilitatea serverului.
```

### Prompt 6.3: cache local pentru lista modelelor

```text
Task:
Adauga cache local pentru lista de modele Ollama, cu TTL simplu.

Constraints:
- Pastreaza implementarea simpla.
- Cache-ul trebuie invalidat dupa import, creare sau stergere de model.
- Nu schimba API-ul public daca nu este necesar.

Output:
- Cod complet.
- Explica unde este stocat cache-ul si cum se invalideaza.
```

## Faza 7: incarcare model cu confirmare reala

### Prompt 7.1: comanda de run non-interactiv

```text
Context:
Respecta fluxul din TAURI_RUST_REBUILD_SPEC.md pentru activarea unui model.

Task:
Implementeaza functia care ruleaza:
`ollama run MODEL "" --keepalive DURATA`

Constraints:
- Nu considera succesul confirmat imediat dupa exit code 0.
- Pregateste functia pentru pasul urmator de confirmare reala.
- Returneaza suficiente detalii pentru diagnostic.

Output:
- Cod complet.
- Explica semnificatia rezultatului returnat.
```

### Prompt 7.2: confirmare activare model

```text
Task:
Adauga logica de confirmare reala a activarii modelului dupa `ollama run`.

Constraints:
- Timeout de baza: 90 secunde.
- Fereastra suplimentara dupa iesirea procesului: 20 secunde.
- Timeout efectiv: `max(size_gb * 8, 90s)`.
- Verifica repetat modelul activ pana la confirmare sau timeout.
- Normalizeaza numele modelului in comparatii.

Output:
- Cod complet.
- Explica de ce aceasta confirmare este mai robusta decat verificarea exit code-ului.
```

### Prompt 7.3: comanda Tauri pentru run model

```text
Task:
Expune prin Tauri comanda `run_ollama_model(name)` folosind logica de activare cu confirmare reala.

Constraints:
- Citeste `keepalive` din setarile aplicatiei.
- Returneaza `CommandResult` clar pentru succes, timeout sau eroare.
- Nu implementa inca progress events complexe.

Output:
- Cod complet.
- Explica contractul returnat frontend-ului.
```

## Faza 8: eject model activ

### Prompt 8.1: stop model activ

```text
Task:
Implementeaza functia care opreste modelul activ folosind `ollama stop MODEL`.

Constraints:
- Detecteaza intai modelul activ.
- Dupa stop, reverifica timp de cateva secunde daca modelul nu mai este activ.
- Returneaza succes doar daca starea s-a schimbat real.

Output:
- Cod complet.
- Explica cum eviti false positives.
```

### Prompt 8.2: comanda Tauri pentru eject

```text
Task:
Expune comanda Tauri `eject_active_model()`.

Constraints:
- Foloseste helperii existenti.
- Returneaza un mesaj clar pentru cazurile fara model activ, succes si esec.

Output:
- Cod complet.
- Modifica minimul necesar.
```

## Faza 9: scanare modele LM Studio

### Prompt 9.1: scanare `.gguf`

```text
Task:
Implementeaza functia Rust care scaneaza recursiv `~/.lmstudio/models` si returneaza fisierele `.gguf` ca `ModelEntry`.

Constraints:
- Sorteaza rezultatele alfabetic.
- Calculeaza size si params daca este posibil.
- Daca folderul lipseste, returneaza lista goala.

Output:
- Cod complet.
- Explica strategia de scanare.
```

### Prompt 9.2: extragere parametri din nume fisier

```text
Task:
Scrie un helper Rust care incearca sa extraga informatii de tip parametri din numele unui model, similar proiectului Python.

Constraints:
- Daca nu exista informatie clara, returneaza `N/A` sau echivalent.
- Functia trebuie sa fie pura.

Output:
- Cod complet.
- Include teste unitare pentru cateva exemple realiste.
```

## Faza 10: import LM Studio -> Ollama

### Prompt 10.1: creare Modelfile temporar

```text
Task:
Implementeaza functia care creeaza temporar un Modelfile cu continutul:
`FROM "/cale/catre/model.gguf"`

Constraints:
- Curata fisierul temporar dupa utilizare.
- Nu lasa fisiere orfane.

Output:
- Cod complet.
- Explica tratamentul cleanup-ului.
```

### Prompt 10.2: import in Ollama

```text
Task:
Implementeaza fluxul Rust care ruleaza:
`ollama create NUME_MODEL -f MODelfile`

Constraints:
- In caz de succes, invalideaza cache-ul modelelor Ollama.
- Returneaza erori explicite.
- Nu incarca inca modelul dupa import in acest pas.

Output:
- Cod complet.
- Explica ce informatii de eroare sunt pastrate.
```

### Prompt 10.3: import plus activare

```text
Task:
Construieste fluxul complet pentru import din LM Studio si apoi activare a modelului importat.

Constraints:
- Dupa import reusit, foloseste exact fluxul existent de `run_ollama_model` cu confirmare reala.
- Nu duplica logica de activare.

Output:
- Cod complet.
- Explica pe scurt secventa completa.
```

## Faza 11: creare model derivat cu `num_ctx`

### Prompt 11.1: helper pentru model derivat

```text
Task:
Implementeaza functia care construieste numele unui model derivat in forma `BASE_NAME-ctxNUMAR`.

Constraints:
- Functie pura.
- Usor de testat.

Output:
- Cod complet.
- Include teste unitare.
```

### Prompt 11.2: creare model cu context custom

```text
Context:
Respecta fluxul din proiectul Python pentru modelele derivate.

Task:
Implementeaza crearea unui model derivat prin Modelfile temporar cu:
- `FROM BASE_NAME`
- `PARAMETER num_ctx NUMAR`

Constraints:
- Ruleaza `ollama create`.
- Invalideaza cache-ul modelelor.
- Salveaza `num_ctx` in setari pentru modelul de baza.

Output:
- Cod complet.
- Explica cum este salvat contextul preferat.
```

### Prompt 11.3: comanda Tauri pentru creare model derivat

```text
Task:
Expune comanda Tauri `create_model_with_context(base_name, num_ctx)`.

Constraints:
- Returneaza `CommandResult`.
- Valideaza input-ul minimal.
- Modifica minimul necesar.

Output:
- Cod complet.
- Explica validarea aplicata.
```

## Faza 12: stergere model Ollama

### Prompt 12.1: `ollama rm`

```text
Task:
Implementeaza functia Rust care sterge un model folosind `ollama rm MODEL`.

Constraints:
- Captureaza stdout si stderr.
- Invalideaza cache-ul la succes.
- Returneaza mesaj clar pentru frontend.

Output:
- Cod complet.
- Explica tratamentul erorilor.
```

### Prompt 12.2: comanda Tauri pentru delete

```text
Task:
Expune comanda Tauri `delete_ollama_model(name)`.

Constraints:
- Refoloseste helperul existent.
- Nu modifica alte fluxuri.

Output:
- Cod complet.
- Explica contractul pentru frontend.
```

## Faza 13: monitorizare resurse

### Prompt 13.1: RAM pentru procese Ollama

```text
Task:
Implementeaza functia Rust care estimeaza RAM-ul folosit de procesele Ollama prin scanarea proceselor de sistem.

Constraints:
- Pastreaza logica simpla.
- Daca nu se poate determina nimic, returneaza zero sau un rezultat gol clar.
- Nu adauga dependinte mari daca nu sunt necesare.

Output:
- Cod complet.
- Explica metoda folosita.
```

### Prompt 13.2: VRAM optional prin nvidia-smi

```text
Task:
Adauga detectia optionala a VRAM prin `nvidia-smi` si coreleaza PIDs cu procesele Ollama.

Constraints:
- Daca `nvidia-smi` nu exista sau esueaza, nu trata cazul ca eroare critica.
- Returneaza doar datele disponibile.

Output:
- Cod complet.
- Explica fallback-ul.
```

### Prompt 13.3: text afisabil pentru resurse

```text
Task:
Construieste formatul text pentru resurse in stilul:
- `RAM: 512.3 MB`
- `RAM: 512.3 MB | VRAM: 2048.0 MB`
- `—` daca nu exista date

Constraints:
- Functie pura.
- Usor de testat.

Output:
- Cod complet.
- Include teste unitare.
```

## Faza 14: wiring comenzi Tauri

### Prompt 14.1: registru de comenzi

```text
Task:
Inregistreaza toate comenzile Tauri implementate pana acum intr-un mod curat si coerent.

Constraints:
- Nu schimba semnaturile comenzilor daca nu este necesar.
- Pastreaza bootstrap-ul usor de citit.

Output:
- Cod complet.
- Explica organizarea finala a comenzilor.
```

### Prompt 14.2: stare partajata backend

```text
Task:
Adauga o stare partajata backend pentru:
- settings
- cache lista modele
- eventuale lock-uri necesare pentru comenzi concurente

Constraints:
- Implementarea trebuie sa fie simpla.
- Evita lock-uri excesive.
- Nu introduce concurenta complicata fara nevoie.

Output:
- Cod complet.
- Explica responsabilitatea fiecarui camp.
```

## Faza 15: frontend principal

### Prompt 15.1: shell UI principal

```text
Context:
Construiesti frontend-ul principal pentru aplicatia Tauri Ollama Control.
Stack-ul frontend este fix: Vanilla TypeScript + Vite + CSS simplu.

Task:
Creeaza layout-ul principal al dashboard-ului cu zone pentru:
- status serviciu
- model activ
- versiune Ollama
- resurse
- butoane principale
- notificari

Constraints:
- Nu folosi biblioteci UI externe.
- Nu introduce framework frontend sau component library.
- Stil sobru, clar, desktop utility app.
- Pastreaza layout-ul responsive decent.

Output:
- Cod complet al layout-ului.
- Stilurile necesare.
- Foloseste fisiere si organizare compatibile cu Vite si Vanilla TypeScript.
```

### Prompt 15.2: componenta StatusCard

```text
Task:
Construieste componenta `StatusCard` care afiseaza:
- badge pentru stare serviciu
- titlu principal
- subtitlu
- uptime
- stare detaliata

Constraints:
- Componenta primeste date prin props.
- Nu face apeluri directe catre backend in componenta.
- Implementeaza componenta in Vanilla TypeScript, fara framework UI.

Output:
- Cod complet.
- Stiluri sau clase asociate.
```

### Prompt 15.3: componenta MetaCard

```text
Task:
Construieste o componenta pentru afisarea:
- model activ
- versiune Ollama
- resurse

Constraints:
- Componenta trebuie sa fie usor de re-renderizat.
- Pastreaza codul simplu.
- Foloseste structura compatibila cu Vanilla TypeScript si DOM API simplu.

Output:
- Cod complet.
- Tipurile necesare.
```

### Prompt 15.4: bara de actiuni principale

```text
Task:
Construieste bara de actiuni principale cu butoanele:
- Setari
- Log
- Porneste
- Restart
- Reimprospateaza
- Opreste

Constraints:
- Butoanele trebuie sa poata fi disabled in functie de stare.
- Nu implementa inca logica completa a fiecarui handler daca nu exista.
- Foloseste elemente native si CSS simplu.

Output:
- Cod complet.
- Explica props-urile componentei.
```

## Faza 16: Model Loader UI

### Prompt 16.1: modal fereastra modele

```text
Task:
Construieste modalul sau view-ul `Model Loader` cu doua taburi:
- LM Studio
- Ollama

Constraints:
- Trebuie sa suporte schimbarea tabului fara resetari inutile.
- Pastreaza structura simpla.
- Implementeaza UI-ul in Vanilla TypeScript + CSS simplu.

Output:
- Cod complet.
- Stilurile necesare.
```

### Prompt 16.2: tabel modele

```text
Task:
Construieste tabelul de modele cu coloanele:
- Stare
- Model
- Dimensiune
- Parametri
- Actiuni

Constraints:
- Sa poata marca vizual modelul activ.
- Sa suporte filtrare dupa nume.
- Sa permita actiuni contextuale pe rand.
- Nu folosi librarii externe de tabel sau grid.

Output:
- Cod complet.
- Tipurile si props-urile.
```

### Prompt 16.3: search/filter local

```text
Task:
Adauga filtrare locala dupa numele modelului in tabelul de modele.

Constraints:
- Filtrarea trebuie sa fie case-insensitive.
- Daca nu exista rezultate, afiseaza un mesaj clar.
- Nu complica inutil state management-ul.

Output:
- Cod complet.
- Explica minimul de stare introdus.
```

### Prompt 16.4: indicator model activ

```text
Task:
Adauga un indicator vizual clar pentru modelul activ in lista de modele.

Constraints:
- Trebuie sa fie lizibil in tema dark si light.
- Nu schimba structura de date daca nu este necesar.

Output:
- Cod complet.
- Explica alegerea de stil.
```

## Faza 17: conectare frontend-backend

### Prompt 17.1: apel status initial

```text
Task:
Conecteaza frontend-ul la comanda Tauri pentru a citi starea initiala a serviciului si a o afisa in dashboard.

Constraints:
- Gestioneaza loading, success si error.
- Pastreaza logica de fetch izolata.
- Foloseste invocari Tauri dintr-un strat `src/api/` sau echivalent simplu.

Output:
- Cod complet.
- Explica locul unde se face invocarea comenzii.
```

### Prompt 17.2: polling controlat

```text
Context:
Respecta strategia de refresh din specificatia proiectului.
Frontend-ul este Vanilla TypeScript + Vite, fara state library.

Task:
Implementeaza polling controlat in frontend pentru refresh-ul dashboard-ului.

Constraints:
- Nu face polling agresiv.
- Permite configurarea prin setari.
- Evita request-uri paralele inutile.
- Pastreaza starea locala simpla, fara framework de state management.

Output:
- Cod complet.
- Explica cum previi suprapunerea refresh-urilor.
```

### Prompt 17.3: comenzi de service din UI

```text
Task:
Conecteaza butoanele de start, stop si restart la comenzile Tauri corespunzatoare.

Constraints:
- Dezactiveaza butoanele pe durata operatiei.
- Afiseaza feedback clar pentru succes sau eroare.
- Nu duplica logica comuna.

Output:
- Cod complet.
- Explica tratamentul starilor tranzitorii.
```

### Prompt 17.4: deschidere log din UI

```text
Task:
Conecteaza butonul `Log` astfel incat sa deschida fisierul de log al aplicatiei.

Constraints:
- Solutie compatibila Linux.
- Returneaza feedback clar daca fisierul nu poate fi deschis.

Output:
- Cod complet.
- Explica mecanismul folosit.
```

## Faza 18: settings UI

### Prompt 18.1: modal setari

```text
Task:
Construieste modalul de setari pentru:
- auto-refresh
- confirmare stop/restart
- keepalive Ollama
- tema
- modele recente

Constraints:
- Leaga formularul la `AppSettings`.
- Pastreaza layout-ul simplu si clar.
- Implementeaza formularul in Vanilla TypeScript + CSS simplu.

Output:
- Cod complet.
- Stilurile necesare.
```

### Prompt 18.2: validare keepalive

```text
Task:
Implementeaza validarea pentru campul `keepalive` cu formate de tip:
- 45s
- 10m
- 2h
- 1d

Constraints:
- Daca valoarea este invalida, afiseaza o eroare clara.
- Nu bloca salvarea altor campuri fara motiv.
- Foloseste validare simpla in frontend, fara biblioteci de formular.

Output:
- Cod complet.
- Explica regula de validare.
```

### Prompt 18.3: save settings din UI

```text
Task:
Conecteaza modalul de setari la comenzile Tauri pentru load/save.

Constraints:
- Dupa salvare, actualizeaza polling-ul daca intervalul s-a schimbat.
- Pastreaza logica de mapare cat mai simpla.
- Foloseste wiring direct intre DOM, stare locala si comenzile Tauri.

Output:
- Cod complet.
- Explica ce se intampla dupa salvare.
```

## Faza 19: fluxuri modele in UI

### Prompt 19.1: listare modele Ollama in UI

```text
Task:
Conecteaza tabul `Ollama` din Model Loader la backend pentru listarea modelelor.

Constraints:
- Afiseaza loading state.
- Daca serverul Ollama nu raspunde, afiseaza un mesaj clar.
- Nu complica fluxul cu optimizari premature.
- Pastreaza implementarea compatibila cu Vanilla TypeScript si DOM API simplu.

Output:
- Cod complet.
- Explica starile UI gestionate.
```

### Prompt 19.2: listare modele LM Studio in UI

```text
Task:
Conecteaza tabul `LM Studio` la backend pentru listarea modelelor `.gguf`.

Constraints:
- Afiseaza fallback clar daca nu exista modele.
- Refoloseste tabelul existent daca este potrivit.
- Nu introduce framework sau data layer suplimentar.

Output:
- Cod complet.
- Explica reutilizarea componentelor.
```

### Prompt 19.3: select model Ollama din UI

```text
Task:
Conecteaza butonul `Select` pentru un model Ollama la comanda `run_ollama_model`.

Constraints:
- Afiseaza progres sau stare de incarcare.
- Dupa succes, actualizeaza modelul activ in UI.
- Dupa esec, afiseaza mesaj clar.
- Pastreaza logica UI locala si simpla.

Output:
- Cod complet.
- Explica fluxul UI.
```

### Prompt 19.4: import model LM Studio din UI

```text
Task:
Conecteaza selectarea unui model LM Studio la fluxul de import si activare.

Constraints:
- Arata o stare de progres simpla.
- Dupa succes, sincronizeaza lista de modele si modelul activ.
- Nu duplica logica de refresh.
- Foloseste doar structura existenta a frontend-ului Vanilla TypeScript.

Output:
- Cod complet.
- Explica secventa de update UI.
```

### Prompt 19.5: eject model din UI

```text
Task:
Conecteaza butonul `Eject Model` la comanda Tauri corespunzatoare.

Constraints:
- Dupa succes, actualizeaza dashboard-ul si indicatorii din lista de modele.
- Gestioneaza cazul fara model activ.
- Nu introduce mecanisme de stare globale daca nu sunt necesare.

Output:
- Cod complet.
- Explica starile tratate.
```

### Prompt 19.6: stergere model din UI

```text
Task:
Adauga actiunea de stergere pentru un model Ollama din lista de modele.

Constraints:
- Cere confirmare in UI.
- Dupa succes, actualizeaza lista.
- Afiseaza erori clare.
- Foloseste componente sau helperi compatibili cu CSS simplu si DOM API.

Output:
- Cod complet.
- Explica fluxul de confirmare.
```

### Prompt 19.7: creare model cu context din UI

```text
Task:
Construieste fluxul UI pentru configurarea `num_ctx` si crearea modelului derivat.

Constraints:
- Ofera optiunile: 2048, 4096, 8192, 16384, 32768, 65536, 128000.
- Dupa succes, refresh lista modelelor.
- Pastreaza formularul simplu.
- Implementeaza dialogul in Vanilla TypeScript, fara librarie UI.

Output:
- Cod complet.
- Explica starea formularului si apelul backend.
```

## Faza 20: notificari si UX

### Prompt 20.1: sistem simplu de notificari

```text
Task:
Construieste un sistem simplu de notificari pentru frontend cu tipuri:
- success
- error
- warning
- info

Constraints:
- Fara dependinte externe.
- Usor de reutilizat din dashboard si din Model Loader.
- Compatibil cu un frontend Vanilla TypeScript bazat pe DOM API.

Output:
- Cod complet.
- Explica modelul de stare pentru notificari.
```

### Prompt 20.2: confirmari pentru actiuni riscante

```text
Task:
Adauga confirmari pentru:
- stop
- restart
- stergere model

Constraints:
- Respecta setarea `confirm_before_stop`.
- Nu dubla componentele daca exista un dialog reutilizabil.

Output:
- Cod complet.
- Explica cand apare fiecare confirmare.
```

## Faza 21: polish si rezilienta

### Prompt 21.1: reducere refresh inutil

```text
Task:
Revizuieste polling-ul si actualizeaza implementarea astfel incat:
- statusul serviciului sa se citeasca mai rar decat restul datelor;
- resursele sa nu fie citite daca serviciul este oprit;
- refresh-urile sa nu se suprapuna.

Constraints:
- Pastreaza comportamentul usor de inteles.
- Nu introduce optimizari premature complicate.

Output:
- Cod complet.
- Explica optimizarile aplicate.
```

### Prompt 21.2: hardening parsare CLI

```text
Task:
Revizuieste functiile de parsare pentru output-ul `ollama list`, `ollama ps` si `ollama --version`.

Constraints:
- Concentreaza-te pe robustete la spatii multiple, output partial si linii neasteptate.
- Nu schimba API-urile externe fara motiv.

Output:
- Cod complet.
- Explica edge cases acoperite.
```

### Prompt 21.3: review tehnic local

```text
Task:
Fa un review tehnic asupra fisierului sau modulului curent.

Concentreaza-te strict pe:
- bug-uri reale
- regresii de comportament
- blocaje concurente
- erori de parsare
- erori de gestionare a proceselor externe
- compatibilitate Linux

Output:
- Daca exista probleme, da-le intai, clar si concret.
- Daca nu exista probleme evidente, spune explicit asta si mentioneaza riscurile ramase.
```

## Prompturi de reparatie dupa erori reale

### Prompt R1: eroare de compilare Rust

```text
Task:
Repara strict eroarea de compilare de mai jos.

Constraints:
- Modifica minimul necesar.
- Nu schimba arhitectura.
- Nu introduce dependinte noi daca nu este obligatoriu.

Error:
[lipeste aici eroarea exacta de la cargo check]

Output:
- Da patch-ul exact.
- Explica de ce aparea eroarea.
```

### Prompt R2: eroare frontend

```text
Task:
Repara strict eroarea frontend de mai jos.

Constraints:
- Pastreaza structura actuala.
- Modifica minimul necesar.
- Respecta stack-ul fix: Vanilla TypeScript + Vite + CSS simplu.

Error:
[lipeste eroarea exacta din consola sau build]

Output:
- Da patch-ul exact.
- Explica cauza.
```

### Prompt R3: bug de comportament

```text
Context:
Exista un bug de comportament intr-un flux deja implementat.

Task:
Identifica si repara bug-ul descris mai jos.

Bug:
[descriere scurta + pasi de reproducere + output real]

Constraints:
- Concentreaza-te pe cauza locala.
- Nu porni refactorizare larga.
- Modifica minimul necesar.

Output:
- Explica cauza probabila.
- Da schimbarea exacta.
- Mentioneaza ce verificare ar trebui rulata dupa patch.
```

### Prompt R4: raspunsul modelului a deraiat

```text
Ignora propunerea anterioara larga.
Rezolva strict task-ul local de mai jos.
Nu modifica alte fisiere daca nu este absolut necesar.
Nu schimba arhitectura.
Nu propune alternative largi.

Task:
[task local foarte concret]
```

## Prompturi de validare

### Prompt V1: teste unitare pentru parser

```text
Task:
Scrie teste unitare doar pentru functiile pure de parsare din acest fisier.

Acopera:
- input valid
- input gol
- linii incomplete
- spatii multiple
- valori neasteptate

Constraints:
- Nu incerca sa testezi procese reale de sistem in acest pas.

Output:
- Cod complet al testelor.
- Explica acoperirea.
```

### Prompt V2: pregatire pentru code review

```text
Task:
Pregateste acest modul pentru code review tehnic.

Constraints:
- elimina cod evident mort daca exista;
- clarifica nume slabe;
- extrage helperi mici doar daca reduc complexitatea;
- nu schimba comportamentul extern.

Output:
- Codul actualizat.
- Lista scurta a imbunatatirilor facute.
```

## Ordine recomandata de folosire

Ordinea buna pentru aceste prompturi este:

1. Faza 1-3 pentru fundatie;
2. Faza 4-14 pentru backend complet;
3. Faza 15-20 pentru frontend si UX;
4. Faza 21 + prompturile R/V pentru hardening.

## Regula finala

Daca un prompt devine prea mare, taie-l in jumatate.

Pentru `qwen2.5-coder-7b-instruct`, aceasta regula valoreaza mai mult decat orice formulare sofisticata.