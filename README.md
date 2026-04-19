# webprint

`webprint` to mała aplikacja Flask do wysyłania plików do drukarki skonfigurowanej w CUPS przez prosty interfejs WWW. Aktualny stan repozytorium jest bardzo prosty: cała logika aplikacji znajduje się w jednym pliku `app.py`, a interfejs HTML/CSS/JavaScript jest osadzony bezpośrednio w kodzie.

## Cel aplikacji

Celem projektu jest udostępnienie lekkiego webowego panelu do:

- przesyłania plików do wydruku,
- podglądu historii ostatnich wydruków,
- sprawdzania stanu drukarki,
- podglądu kolejki CUPS,
- anulowania zadania drukowania po `job-id`.

## Aktualne funkcje

Na podstawie aktualnego kodu aplikacja udostępnia:

- prosty widok `Podstawowy` z uploadem pliku i wywołaniem `POST /api/print`,
- widok `Zaawansowany` z formularzem zawierającym pola `copies`, `scale`, `orientation`, `color`, `quality`,
- widok `Historia` odświeżany cyklicznie przez `GET /api/history`,
- widok `Kolejka` odświeżany cyklicznie przez `GET /api/status`,
- anulowanie zadania przez `POST /api/cancel`,
- zapis historii do pliku JSON,
- prosty cache odpowiedzi kolejki CUPS w pamięci procesu.

Ważne ograniczenia aktualnego stanu:

- formularz `Zaawansowany` pokazuje dodatkowe opcje, ale backend ich nie wykorzystuje podczas wywołania `lp`; realnie drukowanie odbywa się komendą `lp -d brother <plik>`,
- aplikacja zakłada istnienie drukarki CUPS o nazwie `brother`,
- aplikacja nie ma wbudowanego uwierzytelniania ani autoryzacji,
- repozytorium nie zawiera gotowych plików `systemd`, konfiguracji Cloudflare Tunnel ani Cloudflare Access.

## Architektura aplikacji

Aktualna architektura jest jednoplikowa:

- `app.py` definiuje konfigurację, logikę biznesową, integrację z CUPS, szablon UI oraz wszystkie endpointy Flask,
- UI jest renderowane przez `render_template_string(...)` z jednego łańcucha HTML,
- historia jest przechowywana jako JSON poza repozytorium, domyślnie w `/opt/webprint/history.json`,
- uploadowane pliki są zapisywane tymczasowo w `/tmp/webprint`,
- kolejka drukarki jest pobierana z CUPS i cache'owana w pamięci procesu przez 2 sekundy.

Przepływ żądania dla wydruku:

1. Użytkownik wysyła plik z formularza.
2. Flask odbiera `request.files["file"]`.
3. Plik jest zapisywany do `/tmp/webprint/<uuid>_<nazwa>`.
4. Aplikacja uruchamia `lp -d brother <ścieżka>`.
5. Po sukcesie dopisywany jest wpis do historii.
6. UI dostaje komunikat JSON albo tekstowy, zależnie od widoku.

## Upload plików

Mechanizm uploadu w aktualnej wersji:

- endpoint podstawowy: `POST /api/print`,
- endpoint widoku zaawansowanego: `POST /advanced`,
- zapis pliku: funkcja `save_upload(file)`,
- lokalizacja: `/tmp/webprint`,
- nazwa pliku: `<uuid>_<oryginalna_nazwa>`.

Aktualny kod nie robi:

- walidacji rozszerzenia,
- walidacji typu MIME,
- limitowania rozmiaru pliku,
- skanowania bezpieczeństwa,
- automatycznego czyszczenia starych plików z katalogu uploadu.

## Obsługiwane formaty plików

Repozytorium nie definiuje jawnej listy obsługiwanych formatów. Po stronie Flask:

- pole `<input type="file">` nie ogranicza rozszerzeń,
- backend nie filtruje typów plików,
- aplikacja przekazuje zapisany plik bezpośrednio do `lp`.

W praktyce oznacza to, że faktycznie obsługiwane formaty zależą od:

- konfiguracji CUPS,
- dostępnych filtrów drukowania w systemie,
- możliwości konkretnej drukarki `brother`.

Z perspektywy kodu można uczciwie powiedzieć tylko tyle: aplikacja próbuje wysłać dowolny przesłany plik do CUPS, a ostateczna obsługa formatu zależy od systemu drukowania.

## Integracja z CUPS

Integracja z CUPS jest bezpośrednia i opiera się na wywołaniach systemowych:

- status drukarki: `lpstat -p brother`,
- kolejka: `lpstat -o brother`,
- drukowanie: `lp -d brother <plik>`,
- anulowanie: `cancel <job-id>`.

Konsekwencje tej implementacji:

- nazwa drukarki jest na sztywno ustawiona na `brother`,
- aplikacja wymaga obecności narzędzi CLI CUPS w systemie,
- przy błędach `get_printer()` zwraca `Brak danych`,
- przy błędach `get_queue()` zwraca `Brak kolejki`,
- przy błędach drukowania zwracany jest traceback Pythona.

## Historia wydruków

Historia działa lokalnie w pliku JSON:

- ścieżka: `/opt/webprint/history.json`,
- format wpisu: `{ "time": "...", "file": "..." }`,
- nowe wpisy są dodawane na początek listy,
- przechowywane jest maksymalnie 50 ostatnich wpisów,
- przy braku pliku lub błędzie odczytu aplikacja zwraca pustą listę.

To nie jest pełny log wydruków z CUPS. Historia zapisuje tylko:

- czas zapisany przez aplikację,
- oryginalną nazwę pliku.

Nie są zapisywane m.in.:

- `job-id`,
- użytkownik,
- liczba kopii,
- status ukończenia zadania,
- błąd z CUPS po stronie historii.

## Kolejka

Widok kolejki opiera się na wyniku `lpstat -o brother`.

Aktualne zachowanie:

- frontend odświeża status co 2 sekundy,
- backend trzyma wynik kolejki w prostym cache przez 2 sekundy,
- anulowanie zadania odbywa się po ręcznym podaniu `job-id`,
- endpoint `/api/cancel` zawsze zwraca `{"ok": true}`, niezależnie od skuteczności anulowania.

Nie ma tu osobnego systemu kolejkowania po stronie aplikacji. `webprint` jedynie odczytuje i steruje kolejką CUPS.

## Cache

Cache w aktualnym projekcie jest minimalny:

- zmienna globalna `QUEUE_CACHE = {"data": "", "time": 0}`,
- TTL cache: `2` sekundy,
- cache dotyczy tylko wyniku `get_queue()`,
- cache działa wyłącznie w pamięci bieżącego procesu Flask.

To oznacza, że:

- po restarcie procesu cache znika,
- status drukarki nie jest cache'owany,
- historia nie jest cache'owana,
- przy wielu procesach aplikacji każdy proces będzie miał własny cache.

## Integracja z Cloudflare Access

W aktualnym repozytorium nie ma bezpośredniej integracji z Cloudflare Access:

- brak middleware,
- brak sprawdzania nagłówków Access,
- brak walidacji tożsamości w aplikacji,
- brak plików konfiguracyjnych Cloudflare.

Jeżeli aplikacja ma być chroniona przez Cloudflare Access, to w obecnym modelu będzie to zabezpieczenie zewnętrzne, przed Flaskiem, np.:

- `cloudflared` wystawiający lokalny serwis HTTP,
- polityka Access wymuszająca logowanie przed dostępem do hosta.

### Przykładowy model wdrożenia z Cloudflare Access

Poniżej przykład architektury zgodnej z aktualnym projektem, ale niewchodzącej w skład repo:

1. `webprint` nasłuchuje lokalnie na `127.0.0.1:5000` albo `0.0.0.0:5000`.
2. `cloudflared` wystawia tunel do tej usługi.
3. Cloudflare Access chroni publiczny hostname.
4. Użytkownik po uwierzytelnieniu dostaje dostęp do panelu drukowania.

Repozytorium nie zawiera gotowej konfiguracji, ale przykładowy `config.yml` dla `cloudflared` może wyglądać tak:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /etc/cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: print.example.com
    service: http://127.0.0.1:5000
  - service: http_status:404
```

Przykładowa procedura Access:

1. Dodać aplikację self-hosted w Cloudflare Zero Trust.
2. Przypisać hostname tunelu, np. `print.example.com`.
3. Skonfigurować politykę dostępu dla wybranych użytkowników lub grup.
4. Nie wystawiać aplikacji bezpośrednio do Internetu bez warstwy ochronnej.

## Integracja z Cloudflare Tunnel

Tak samo jak w przypadku Access, repo nie zawiera konfiguracji tunelu, ale obecna aplikacja nadaje się do wystawienia przez Cloudflare Tunnel jako zwykła usługa HTTP.

Przykładowe kroki:

1. Zainstalować `cloudflared` na serwerze.
2. Utworzyć i zalogować tunel:

```bash
cloudflared tunnel login
cloudflared tunnel create webprint
```

3. Przygotować `config.yml` wskazujący na lokalny serwis Flask.
4. Dodać DNS route dla hosta.
5. Uruchomić tunel jako usługę systemową.

Przykład:

```bash
cloudflared tunnel route dns webprint print.example.com
cloudflared service install
```

To są kroki wdrożeniowe wokół projektu, a nie część obecnego kodu aplikacji.

## Wymagania systemowe

Z aktualnego kodu wynikają następujące wymagania:

- Linux lub inny system uniksowy z dostępem do:
  - `/tmp/webprint`,
  - `/opt/webprint/history.json`,
  - poleceń `lp`, `lpstat`, `cancel`,
- Python 3,
- Flask,
- skonfigurowany CUPS,
- drukarka dostępna w CUPS pod nazwą `brother`,
- uprawnienia do zapisu w `/tmp/webprint` i `/opt/webprint`.

Uwaga praktyczna: repo jest analizowane na Windows bez problemu jako kod źródłowy, ale sama aplikacja w obecnej formie jest ewidentnie przygotowana do uruchamiania na systemie linuksowym ze względu na ścieżki i polecenia CUPS.

## Instalacja krok po kroku

Ponieważ repo nie zawiera `requirements.txt`, instalacja jest obecnie ręczna.

### 1. Pobranie kodu

```bash
git clone <URL_REPOZYTORIUM>
cd webprint
```

### 2. Przygotowanie środowiska Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install Flask
```

### 3. Przygotowanie katalogów systemowych

```bash
sudo mkdir -p /opt/webprint
sudo mkdir -p /tmp/webprint
sudo chown -R $USER:$USER /opt/webprint /tmp/webprint
```

### 4. Upewnienie się, że CUPS działa

```bash
lpstat -p
```

### 5. Uruchomienie aplikacji

```bash
python3 app.py
```

Po starcie aplikacja nasłuchuje domyślnie na porcie `5000`.

## Konfiguracja drukarki CUPS

Aktualny kod zakłada sztywno nazwę drukarki `brother`, więc w CUPS musi istnieć kolejka dokładnie o tej nazwie.

Sprawdzenie drukarek:

```bash
lpstat -p
```

Dodanie lub zmiana nazwy drukarki zależy od lokalnej konfiguracji CUPS. Jeżeli drukarka ma inną nazwę niż `brother`, obecna aplikacja nie będzie z nią działała bez zmian w kodzie.

Przykładowe polecenia diagnostyczne:

```bash
lpstat -p brother
lpstat -o brother
lpoptions -p brother -l
```

## Uruchamianie jako systemd service

Repozytorium nie zawiera gotowego pliku usługi `systemd`, ale poniżej jest przykład zgodny z aktualnym zachowaniem aplikacji.

Przykładowy plik `/etc/systemd/system/webprint.service`:

```ini
[Unit]
Description=webprint Flask print gateway
After=network.target cups.service

[Service]
User=www-data
WorkingDirectory=/opt/webprint/app
ExecStart=/opt/webprint/app/venv/bin/python /opt/webprint/app/app.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Następnie:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webprint
sudo systemctl start webprint
sudo systemctl status webprint
```

Ważne:

- to jest przykład wdrożeniowy, nie plik obecny w repo,
- użytkownik usługi musi mieć dostęp do CUPS oraz do katalogów `/tmp/webprint` i `/opt/webprint`,
- przy wdrożeniu produkcyjnym lepiej uruchamiać aplikację za reverse proxy lub tunelem, a nie wystawiać bezpośrednio.

## Aktualizacja przez GitHub

Repo jest wersjonowany w Git, więc aktualizacja może wyglądać standardowo:

```bash
cd /opt/webprint/app
git pull
source venv/bin/activate
pip install Flask
sudo systemctl restart webprint
```

Jeżeli w przyszłości pojawi się `requirements.txt`, ten krok powinien zostać zmieniony na:

```bash
pip install -r requirements.txt
```

## Struktura plików projektu

Aktualna struktura repozytorium jest bardzo mała:

```text
webprint/
├── app.py
└── .gitignore
```

Dodatkowe ścieżki używane przez aplikację poza repo:

- `/tmp/webprint` - katalog uploadów tymczasowych,
- `/opt/webprint/history.json` - plik historii wydruków.

## Typowe problemy i troubleshooting

### `Brak danych` w statusie drukarki

Możliwe przyczyny:

- CUPS nie działa,
- drukarka `brother` nie istnieje,
- proces aplikacji nie ma dostępu do polecenia `lpstat`.

Diagnostyka:

```bash
lpstat -p brother
which lpstat
systemctl status cups
```

### `Brak kolejki` w widoku kolejki

Możliwe przyczyny:

- brak aktywnych zadań,
- błąd `lpstat -o brother`,
- problem z nazwą drukarki.

Diagnostyka:

```bash
lpstat -o brother
```

### Drukowanie kończy się tracebackiem

To oznacza, że polecenie `lp` zwróciło błąd albo przekroczyło timeout.

Diagnostyka:

```bash
lp -d brother /sciezka/do/pliku
lpstat -p brother
lpstat -o brother
```

### Historia się nie zapisuje

Możliwe przyczyny:

- brak katalogu `/opt/webprint`,
- brak uprawnień do zapisu,
- uszkodzony plik JSON.

Diagnostyka:

```bash
ls -ld /opt/webprint
ls -l /opt/webprint/history.json
```

### Opcje z widoku `Zaawansowany` niczego nie zmieniają

To nie jest błąd konfiguracji serwera, tylko obecny stan implementacji. Formularz zawiera pola dodatkowe, ale backend ich nie przekazuje do komendy `lp`.

## Bezpieczeństwo

Z punktu widzenia bezpieczeństwa obecna wersja projektu jest minimalna i wymaga ochrony infrastrukturalnej.

Faktyczny stan:

- brak logowania w aplikacji,
- brak autoryzacji,
- brak walidacji typów plików,
- brak limitów uploadu,
- brak izolacji użytkowników,
- brak filtrowania nazw plików poza prefiksem UUID,
- brak mechanizmu usuwania starych uploadów,
- błędy drukowania mogą ujawniać traceback.

Minimalne rekomendacje wdrożeniowe bez zmiany logiki aplikacji:

- nie wystawiać aplikacji bezpośrednio do publicznego Internetu,
- postawić przed nią Cloudflare Tunnel i Cloudflare Access,
- ograniczyć dostęp do wybranych użytkowników,
- uruchamiać usługę z możliwie małymi uprawnieniami,
- monitorować rozmiar katalogu `/tmp/webprint`,
- regularnie tworzyć kopię `history.json`, jeżeli historia ma znaczenie operacyjne.

## Możliwe przyszłe rozszerzenia

Poniższe elementy nie istnieją obecnie w repo, ale wynikają naturalnie z aktualnej architektury:

- realna obsługa parametrów z formularza `Zaawansowany`,
- konfiguracja nazwy drukarki przez zmienną środowiskową lub plik konfiguracyjny,
- `requirements.txt`,
- gotowe jednostki `systemd` i przykładowe pliki `cloudflared`,
- walidacja typów plików i limit rozmiaru uploadu,
- czyszczenie starych plików z `/tmp/webprint`,
- zapisywanie `job-id` do historii,
- lepsza obsługa błędów bez zwracania tracebacku do użytkownika,
- prosty panel administracyjny,
- logowanie zdarzeń do sysloga lub pliku.

## Podsumowanie stanu projektu

Aktualny `webprint` jest lekką, jednoplikową aplikacją Flask będącą cienką warstwą WWW nad komendami CUPS dla drukarki `brother`. Projekt ma działający upload, drukowanie, podgląd historii i kolejki, ale nie zawiera jeszcze kompletnej warstwy wdrożeniowej ani bezpieczeństwa w samym kodzie. `README.md` w tym repo opisuje więc zarówno to, co naprawdę istnieje dziś, jak i zewnętrzne przykłady wdrożenia, wyraźnie oznaczone jako elementy spoza repozytorium.
