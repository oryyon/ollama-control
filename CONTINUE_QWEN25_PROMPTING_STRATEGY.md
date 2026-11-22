# Strategie De Prompting Pentru Continue Cu qwen2.5-coder-7b-instruct

## Scop

Acest ghid este conceput pentru dezvoltarea noului proiect Ollama Control in Tauri + Rust folosind:

- Kubuntu 24.04
- Intel i3-5005U
- 12 GB RAM
- Ollama
- modelul `qwen2.5-coder:7b`
- VS Code + Continue

Obiectivul nu este sa obtii toata aplicatia dintr-un singur prompt, ci sa folosesti modelul eficient, predictibil si cu consum rezonabil de resurse.

## Principiul de baza

Acest model trebuie tratat ca un executor bun pentru task-uri mici si bine delimitate, nu ca un arhitect autonom pentru un proiect intreg.

Formula corecta este:

1. defineste exact o singura bucata de lucru;
2. da-i context minim, dar suficient;
3. cere output concret, nu brainstorming;
4. valideaza imediat;
5. abia apoi treci la pasul urmator.

Pe laptopul tau, aceasta abordare este mai importanta decat orice prompt "smart".

## Ce face bine modelul

`qwen2.5-coder-7b-instruct` este potrivit pentru:

- generare de fisiere mici si medii;
- implementare de functii bine specificate;
- parsare output CLI;
- wiring intre componente Rust si frontend Tauri;
- refactorizari locale;
- completare de tipuri, structuri si DTO-uri;
- scriere de comenzi Tauri individuale;
- ajustari UI punctuale;
- documentatie tehnica pragmatica.

## Ce face mai slab

Modelul devine nesigur cand ii ceri:

- sa proiecteze toata aplicatia dintr-un singur pas;
- sa tina minte multe fisiere mari simultan;
- sa faca modificari late in 6-10 fisiere fara ghidaj strict;
- sa rezolve singur bug-uri ambigue fara output concret de eroare;
- sa aleaga intre mai multe directii arhitecturale fara constrangeri;
- sa produca cod si design final in acelasi prompt mare.

## Regula de aur pentru Continue

Fiecare prompt trebuie sa aiba maxim 4 blocuri:

1. `Context`
2. `Task`
3. `Constraints`
4. `Output`

Nu amesteca cerinte generale, idei, intrebari si cod in acelasi mesaj daca vrei consistenta.

## Template-ul recomandat

Foloseste constant acest sablon:

```text
Context:
Lucrezi la rescrierea proiectului Ollama Control in Tauri + Rust.
Consulta TAURI_RUST_REBUILD_SPEC.md si respecta fluxurile existente.

Task:
Implementeaza [o singura functie / un singur fisier / un singur flux local].

Constraints:
- Nu modifica alte fisiere in afara de cele necesare.
- Pastreaza codul simplu si compatibil Linux.
- Nu adauga dependinte noi fara motiv clar.
- Nu lasa TODO-uri daca implementarea poate fi terminata acum.

Output:
- Scrie codul complet.
- Explica pe scurt ce ai schimbat.
- Daca exista incertitudini, semnaleaza-le explicit.
```

## Reguli de prompting pentru hardware-ul tau

Pe `i3-5005U` cu `12 GB RAM`, costul principal este latenta si degradarea raspunsului la prompturi prea mari.

De aceea:

- evita prompturi mai mari decat este necesar;
- nu lipi fisiere mari integral daca modelul poate citi direct din workspace;
- cere lucruri locale, nu "analizeaza tot repo-ul";
- sparge task-urile pe verticala;
- evita atasarea simultana a mai mult de 2-3 fisiere mari;
- cere mai intai implementare, apoi polish;
- dupa fiecare pas ruleaza validare si ofera eroarea exacta inapoi modelului.

## Tipuri de prompturi care functioneaza bine

### 1. Prompt de implementare locala

Acesta este cel mai sigur tip de prompt.

```text
Context:
Lucrezi la backend-ul Rust pentru Ollama Control. Respecta TAURI_RUST_REBUILD_SPEC.md.

Task:
Implementeaza comanda Tauri `get_service_status()` in src-tauri/src/commands/service.rs.
Comanda trebuie sa ruleze `systemctl is-active ollama`, `systemctl show ollama --property=SubState --value` si `systemctl show ollama --property=ActiveEnterTimestamp --value`.

Constraints:
- Foloseste Rust async doar daca este necesar.
- Returneaza un struct serializabil cu `active_state`, `sub_state`, `active_timestamp` si `uptime_text`.
- Nu implementa alte comenzi in acest pas.

Output:
- Scrie codul complet.
- Daca ai nevoie de functii helper, adauga-le local in acelasi modul.
```

### 2. Prompt de reparare bazat pe eroare reala

Acesta este foarte eficient pentru un model de 7B.

```text
Context:
Lucrezi la proiectul Tauri + Rust pentru Ollama Control.

Task:
Repara eroarea de compilare din src-tauri/src/commands/models.rs.

Constraints:
- Nu schimba API-ul public daca nu este necesar.
- Modifica minimul necesar.

Error:
[paste exact eroarea de compilare]

Output:
- Da patch-ul exact.
- Explica de ce aparea eroarea.
```

### 3. Prompt de parsare CLI

Modelul merge bine cand inputul si outputul sunt precise.

```text
Task:
Scrie o functie Rust care parseaza output-ul comenzii `ollama list` intr-un `Vec<ModelEntry>`.

Input example:
NAME            ID              SIZE    MODIFIED
qwen2.5:7b      abc123          4.7 GB  2 days ago

Constraints:
- Toleranta la spatii multiple.
- Daca header-ul nu este prezent, returneaza lista goala.
- Extrage `name` si `size`.

Output:
- Cod Rust complet.
- Include 2 teste unitare.
```

### 4. Prompt de UI punctual

```text
Context:
Frontend Tauri pentru Ollama Control.

Task:
Construieste componenta `StatusCard` care afiseaza badge-ul serviciului, uptime-ul si subtitlul de stare.

Constraints:
- Nu folosi librarii UI externe.
- Pastreaza paleta sobra, orientata pe Linux desktop utility app.
- Componenta trebuie sa accepte date prin props.

Output:
- Cod complet al componentei.
- Stilurile necesare.
```

## Tipuri de prompturi care merg prost

Evita formule ca:

- `Fa-mi toata aplicatia in Tauri + Rust.`
- `Creeaza cea mai buna arhitectura posibila.`
- `Refa tot proiectul modern.`
- `Analizeaza tot repo-ul si propune tot.`
- `Fa backend-ul complet, UI-ul complet si testele.`

Acestea par eficiente, dar pe un model de 7B produc de obicei:

- omisiuni;
- fisiere inventate;
- API-uri inconsistente;
- explicatii prea generale;
- cod neverificat.

## Strategia corecta pe etape

Pentru acest proiect, ordinea buna de lucru in Continue este:

1. setup proiect Tauri;
2. modelarea structurilor de date comune;
3. comenzi pentru status serviciu;
4. comenzi pentru versiune Ollama si model activ;
5. listare modele Ollama;
6. incarcare model cu confirmare reala;
7. eject model;
8. creare model derivat cu `num_ctx`;
9. monitorizare resurse;
10. UI principal;
11. fereastra modele;
12. setari persistente;
13. polish si validare.

Nu sari peste ordinea asta daca vrei sa reduci erorile cumulative.

## Strategia pe sesiuni scurte

Pe hardware-ul tau, sesiunile lungi degradeaza utilitatea modelului. Mai bine lucrezi in cicluri scurte.

Format recomandat pentru o sesiune:

1. deschizi un singur obiectiv clar;
2. ceri o singura implementare;
3. rulezi build sau test;
4. revii cu eroarea exacta;
5. inchizi sub-task-ul;
6. treci la urmatorul.

Durata buna a unei sesiuni continue pe acelasi subiect:

- 10-25 minute;
- 1-3 fisiere atinse;
- 1 singur flux functional.

## Ce context sa dai mereu

Pentru acest proiect, modelul ar trebui sa primeasca frecvent urmatorul context minim:

- faptul ca proiectul tinta este Tauri + Rust;
- faptul ca trebuie pastrata compatibilitatea functionala cu specificatia din `TAURI_RUST_REBUILD_SPEC.md`;
- faptul ca aplicatia ruleaza pe Linux cu `systemd`, `pkexec` si `ollama` CLI;
- faptul ca laptopul este modest si solutia trebuie sa fie simpla si eficienta.

Exemplu scurt bun:

```text
Respecta TAURI_RUST_REBUILD_SPEC.md. Tinta este Linux desktop utility app in Tauri + Rust, cu comenzi reale catre systemd si ollama. Solutia trebuie sa fie simpla, robusta si potrivita pentru hardware modest.
```

## Ce sa ceri explicit modelului

Formule utile:

- `modifica minimul necesar`
- `nu presupune fisiere inexistente`
- `scrie cod complet, nu pseudocod`
- `nu introduce dependinte noi fara justificare`
- `respecta structura deja existenta`
- `include un test local daca e fezabil`
- `explica de ce schimbarea este corecta`
- `daca exista ambiguitate, alege varianta mai simpla`

Aceste instructiuni reduc raspunsurile speculative.

## Cum sa ceri review de cod

Pentru review, nu cere opinie generala. Cere defecte concrete.

Prompt bun:

```text
Revizuiește schimbările din acest fișier ca un code review tehnic.
Concentrează-te pe:
- bug-uri reale
- regresii de comportament
- probleme de concurență
- parsare fragilă
- edge cases
- compatibilitate Linux

Nu face rezumat lung. Dă întâi problemele concrete, dacă există.
```

## Cum sa ceri refactorizare

Nu spune doar `refactorizeaza`. Spune ce anume vrei imbunatatit.

Prompt bun:

```text
Refactorizeaza acest modul pentru a separa:
- executia de comenzi shell
- parsarea output-ului
- maparea in structuri serializabile

Constraints:
- fara schimbarea comportamentului extern;
- fara dependinte noi;
- mentine fisierul usor de testat.
```

## Cum sa ceri testare

Prompt bun:

```text
Scrie teste unitare doar pentru functiile pure din acest fisier.
Acopera:
- parsare output valid
- input gol
- linii incomplete
- spatii multiple

Nu incerca sa testezi comenzile shell reale in acest pas.
```

## Cum sa recuperezi cand modelul deraiaza

Daca raspunsul devine vag sau inventeaza lucruri:

1. opreste promptul mare;
2. revino cu un task mai mic;
3. elimina jumatate din context;
4. cere modificari intr-un singur fisier;
5. da eroarea sau outputul exact;
6. cere patch minim.

Prompt de reset bun:

```text
Ignora propunerea anterioara larga.
Rezolva strict acest task local.
Nu modifica alte fisiere.
Nu schimba arhitectura.
```

## Mod de lucru recomandat pentru noul Ollama Control

Pentru rescrierea acestui proiect, cel mai eficient flux in Continue este:

### Faza 1: backend stabil

Prompts pentru:

- structuri `ServiceStatus`, `ModelEntry`, `AppSettings`, `CommandResult`;
- comenzi Tauri individuale;
- functii helper pentru rulare de procese;
- parsare output `systemctl`, `ollama list`, `ollama ps`;
- persistenta setari JSON.

### Faza 2: fluxurile critice

Prompts pentru:

- `run_ollama_model()` cu timeout si confirmare reala;
- `eject_active_model()`;
- `create_model_with_context()`.

### Faza 3: UI

Prompts pentru:

- dashboard principal;
- model loader modal;
- settings modal;
- notificari;
- polling orchestration in frontend.

### Faza 4: polish

Prompts pentru:

- tratament erori;
- mesaje clare pentru utilizator;
- optimizari mici de refresh;
- testele pentru parsare si helperi.

## Prompturi gata de folosit

### Prompt 1: inceput de sesiune

```text
Lucrezi la rescrierea proiectului Ollama Control in Tauri + Rust.
Respecta specificatia din TAURI_RUST_REBUILD_SPEC.md.
Mediul tinta este Linux desktop pe hardware modest, deci solutia trebuie sa fie simpla si eficienta.

In aceasta sesiune vreau sa rezolv un singur pas.
Nu propune restructurari mari daca nu sunt necesare.
```

### Prompt 2: implementare backend locala

```text
Context:
Rescriere Ollama Control in Tauri + Rust.
Respecta TAURI_RUST_REBUILD_SPEC.md.

Task:
Implementeaza functia care detecteaza modelul activ folosind mai intai `ollama ps` si apoi fallback pe scanarea proceselor.

Constraints:
- normalizeaza sufixul `:latest`
- returneaza o structura clara, nu text brut
- nu implementa UI in acest pas
- modifica minimul necesar

Output:
- cod complet
- explicatie scurta
- 2 teste pentru parsare daca sunt fezabile
```

### Prompt 3: reparatie dupa build

```text
Task:
Repara strict eroarea de mai jos fara sa schimbi comportamentul extern.

Error:
[pune eroarea exacta de la cargo check]

Constraints:
- modifica minimul necesar
- nu introduce dependinte noi
- pastreaza API-ul curent daca este posibil
```

### Prompt 4: componenta UI

```text
Context:
Frontend Tauri pentru Ollama Control.

Task:
Construieste un tabel de modele cu coloanele `Stare`, `Model`, `Dimensiune`, `Parametri` si actiuni contextuale.

Constraints:
- sa poata marca vizual modelul activ
- sa permita filtrare dupa nume
- sa fie usor de conectat la comenzi Tauri
- nu adauga librarii externe de tabel

Output:
- componenta completa
- tipurile folosite
- stilurile necesare
```

## Concluzie practica

Pentru `qwen2.5-coder-7b-instruct`, cheia nu este un prompt genial, ci disciplina de lucru:

- task-uri mici;
- context minim dar precis;
- output concret;
- validare imediata;
- iteratii scurte.

Daca folosesti Continue in acest mod, modelul poate contribui eficient chiar si pe laptopul tau cu i3-5005U si 12 GB RAM. Daca incerci prompturi mari, vagi si multi-fisier, calitatea va scadea rapid.