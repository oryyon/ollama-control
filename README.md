# Ollama Control

Aplicatie desktop Python bazata pe CustomTkinter pentru controlul serviciului local Ollama si pentru gestionarea modelelor LM Studio/Ollama.

## Documentatie

- [Despre Ollama Control](Despre%20Ollama%20Control) - prezentare generala a aplicatiei si a capabilitatilor principale.
- [TAURI_RUST_REBUILD_SPEC.md](TAURI_RUST_REBUILD_SPEC.md) - specificatie functionala si tehnica pentru rescrierea proiectului in Tauri + Rust.
- [CONTINUE_QWEN25_PROMPTING_STRATEGY.md](CONTINUE_QWEN25_PROMPTING_STRATEGY.md) - ghid practic de prompting pentru Continue, optimizat pentru `qwen2.5-coder-7b-instruct`.
- [CONTINUE_TAURI_RUST_PROMPT_PACK.md](CONTINUE_TAURI_RUST_PROMPT_PACK.md) - set complet de prompturi gata de copiat pentru rescrierea Ollama Control in Tauri + Rust.

## Schimbari recente

- callback-urile de finalizare pentru importul LM Studio sunt mutate pe UI thread pentru a evita accesul Tk din thread-uri de lucru;
- cache-ul listei de modele Ollama este invalidat dupa import, creare si stergere de modele;
- incarcarea unui model Ollama confirma acum activarea modelului inainte de a marca operatia drept reusita in UI;
- afisarea modelului activ foloseste starea reala din backend, fara sa pastreze indefinit ultima selectie locala;
- mesajele de succes din fereastra de modele sunt afisate distinct fata de erori.
- fluxurile Select, detectare model activ si Eject emit acum logging atat in `~/.ollama_control_ui/app.log`, cat si in terminalul din care este pornita aplicatia;
- detectarea si oprirea modelelor trateaza consistent numele raportate de Ollama, inclusiv sufixul `:latest`;
- fluxul LM Studio a fost verificat end-to-end pe un fisier `.gguf` real: import in Ollama, activare, detectare model activ, eject si cleanup.
- fereastra principala include acum un buton `Log` pentru deschiderea rapida a fisierului `~/.ollama_control_ui/app.log`;
- fluxurile Start, Stop si Restart pentru serviciul Ollama emit loguri explicite pentru cererea din UI, executia `pkexec systemctl` si rezultatul final.
- logurile periodice pentru verificarea modelului activ au fost reduse: starile repetitive sunt raportate o singura data, iar detaliile de polling au fost mutate la nivel `debug`.
- refresh-ul pentru starea serviciului systemd ruleaza acum complet in fundal si foloseste un ritm separat, mai rar, fata de restul actualizarilor UI, pentru a evita blocajele scurte ale interfetei.
- la pornire, interfata afiseaza explicit starea `Se verifică serviciul...` pana la primul raspuns din systemd, in locul unei tranzitii brute `necunoscut -> inactive`;
- verificarea versiunii Ollama si monitorizarea resurselor folosesc cache si ritmuri mai rare, iar monitorizarea resurselor este sarita complet cand serviciul Ollama nu ruleaza.
- profilarea startup-ului a aratat ca imaginile sunt neglijabile, iar costul dominant ramas vine din crearea si primul layout al widget-urilor CustomTkinter;
- redraw-ul fortat folosit la afisarea barei de incarcare model a fost eliminat, reducand costul acelui pas de la aproximativ `86 ms` la aproximativ `3 ms`.
- sectiunile `status` si `meta` folosesc acum mai putine containere `CTkFrame`, ceea ce a redus numarul total de widget-uri si a scazut timpul mediu de construire a ferestrei principale de la aproximativ `1387 ms` la aproximativ `718 ms` in profilarea locala.
- pentru modelele din tabul `Ollama`, progresul de incarcare foloseste acum o bara nedeterminata, iar confirmarea activarii asteapta mai mult si continua o perioada scurta chiar si dupa iesirea procesului `ollama run`, pentru a evita falsurile negative pe modele lente.
- daca activarea modelului din tabul `Ollama` expira sau Ollama nu confirma pornirea, UI-ul afiseaza acum un mesaj explicit despre expirarea confirmarii, iar logurile de verificare sunt reduse la schimbari de stare in loc de polling repetitiv.
- incarcarea modelelor din tabul `Ollama` foloseste acum o comanda non-interactiva de warmup (`ollama run MODEL "" --keepalive 10m`), astfel incat aplicatia sa incarce modelul fara a intra intr-o sesiune interactiva care asteapta prompt de chat.
- durata `keepalive` pentru modelele incarcate din tabul `Ollama` este configurabila din fereastra `Setări`, iar mesajul de succes din `Model Loader` spune explicit ca modelul a fost confirmat de Ollama si cat timp ramane incarcat.
- aceeasi durata `keepalive` este afisata si in notificarea de succes din fereastra principala, iar in `Setări` se poate introduce si manual o valoare custom valida, nu doar alege una din preset-uri.
- tabul `Ollama` din `Model Loader` marcheaza acum vizual modelul activ/incarcat printr-un indicator verde direct pe randul modelului.
- indicatorul vizual pentru modelul activ pastreaza acum densitatea initiala a listei, fara spatii verticale mari intre randuri.
- coloanele din `Model Loader` folosesc acum aceeasi aliniere in taburile `LM Studio` si `Ollama`, inclusiv pentru zona rezervata indicatorului de model activ.
- randul modelului activ este acum evidentiat complet, coloana indicatorului are titlul `Stare`, iar sincronizarea indicatorului se actualizeaza live si dupa `Eject` daca fereastra `Model Loader` ramane deschisa.
- latimea coloanelor din lista de modele a fost ajustata astfel incat butonul `Select` sa ramana complet vizibil si in tabul `Ollama`.
- evidentierea randului activ foloseste acum o configuratie compatibila cu CustomTkinter si nu mai produce exceptii la deschiderea sau schimbarea taburilor din `Model Loader`.
- timeout-urile repetate din detectarea modelului activ sunt acum deduplicate in log, astfel incat pornirea lenta a serviciului sa nu mai umple inutil jurnalul cu acelasi warning.
- randurile si header-ul din `Model Loader` folosesc acum coloane fixe bazate pe `grid`, astfel incat valorile din `Dimensiune` si `Parametri` sa ramana perfect aliniate indiferent de lungimea numelui modelului.
- numele foarte lungi ale modelelor sunt acum trunchiate vizual in coloana `Model`, astfel incat sa nu se mai suprapuna peste coloanele `Dimensiune` si `Parametri`.
- evidentierea modelului activ foloseste acum culori diferite pentru mod luminos si mod intunecat, astfel incat contrastul dintre fundal si text sa ramana lizibil in ambele teme.
- butoanele mici din tabul `Ollama` folosesc acum culori armonizate pentru mod luminos si mod intunecat, cu contrast mai bun pentru actiunile de configurare si stergere.
- butonul `Select` foloseste acum aceeasi logica de paleta light/dark ca restul actiunilor din lista, pentru un aspect mai coerent intre teme.
- toate butoanele din `Model Loader`, inclusiv cele din header si cele din lista, folosesc acum stari `hover` si `disabled` uniforme, cu reactivare corecta dupa operatiile de incarcare, configurare sau stergere.
- campul de cautare si bara de progres din `Model Loader` folosesc acum culori adaptate pentru mod luminos si mod intunecat, pentru o interfata mai coerenta intre teme.
- stilizarea butoanelor din `Model Loader` foloseste acum doar argumente compatibile cu versiunea curenta de `CustomTkinter`, iar callback-urile UI pentru notificari si auto-refresh evita accesul la widget-uri deja distruse in timpul inchiderii aplicatiei.

## Pornire locala

```bash
./start.sh
```

Scriptul activeaza mediul virtual din `venv/` si ruleaza `python ollama_control.py`.
