import tkinter as tk
import tkintermapview
from typing import List, Tuple

def create_map_app():
    # 1. Tworzenie głównego okna aplikacji
    root = tk.Tk()
    root.geometry("800x600")
    root.title("System nawigacji - Podgląd trasy")

    # 2. Inicjalizacja widżetu mapy
    # Ustawiamy corner_radius=0, aby mapa wypełniała całe okno bez zaokrąglonych rogów
    map_widget = tkintermapview.TkinterMapView(root, width=800, height=600, corner_radius=0)
    map_widget.pack(fill="both", expand=True)

    # 3. Definicja naszej wyliczonej ścieżki (Lista krotek: [Szerokość, Długość])
    # Możesz tu podpiąć dane ze swojego "jądra" systemu
    path_coordinates: List[Tuple[float, float]] = [
        (53.1325, 23.1688),  # Białystok
        (52.2297, 21.0122),  # Warszawa
        (50.0647, 19.9450)   # Kraków
    ]

    # 4. Konfiguracja widoku mapy
    # Ustawiamy środek mapy (np. na Warszawę) i odpowiedni zoom
    map_widget.set_position(52.2297, 21.0122) 
    map_widget.set_zoom(6)

    # 5. Rysowanie ścieżki na mapie
    path = map_widget.set_path(
        position_list=path_coordinates,
        color="#FF0000",     # Czerwony kolor linii
        width=4              # Grubość linii w pikselach
    )

    # Opcjonalnie: Dodanie znaczników (pinezek) na początku i końcu trasy
    map_widget.set_marker(53.1325, 23.1688, text="Start (Białystok)")
    map_widget.set_marker(50.0647, 19.9450, text="Koniec (Kraków)")

    # 6. Uruchomienie pętli głównej interfejsu graficznego
    root.mainloop()

if __name__ == "__main__":
    create_map_app()