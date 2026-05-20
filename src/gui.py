import tkinter as tk
import tkintermapview
from tkinter import messagebox

from src import enums, routing


class RoutingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("System Nawigacji - Wyznaczanie Trasy")
        self.root.geometry("1000x700")

        self.control_frame = tk.Frame(self.root, width=300, padx=20, pady=20)
        self.control_frame.pack(side="left", fill="y")

        self.map_frame = tk.Frame(self.root)
        self.map_frame.pack(side="right", fill="both", expand=True)

        self.map_widget = tkintermapview.TkinterMapView(self.map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(52.2297, 21.0122)
        self.map_widget.set_zoom(11)

        self.mode_colors = {
            enums.RouteMode.CAR: "#FF0000",
            enums.RouteMode.PUBLIC: "#0000FF",
            enums.RouteMode.PR: "#FF00FF",
            enums.RouteMode.WALK_PUBLIC: "#6495ED",
            enums.RouteMode.WALK_PR: "#FFC0CB"
        }

        self._build_controls()

    def _build_controls(self):
        """Buduje formularz w lewym panelu."""
        tk.Label(self.control_frame, text="Współrzędne Startowe", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_source_lon = tk.Entry(self.control_frame)
        self.entry_source_lon.pack(fill="x", pady=(0, 15))
        self.entry_source_lon.insert(0, "20.9679")

        tk.Label(self.control_frame, text="Szerokość (Lat):").pack(anchor="w")
        self.entry_source_lat = tk.Entry(self.control_frame)
        self.entry_source_lat.pack(fill="x", pady=(0, 5))
        self.entry_source_lat.insert(0, "52.1672")

        tk.Label(self.control_frame, text="Współrzędne Celu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_target_lon = tk.Entry(self.control_frame)
        self.entry_target_lon.pack(fill="x", pady=(0, 15))
        self.entry_target_lon.insert(0, "21.0144")

        tk.Label(self.control_frame, text="Szerokość (Lat):").pack(anchor="w")
        self.entry_target_lat = tk.Entry(self.control_frame)
        self.entry_target_lat.pack(fill="x", pady=(0, 5))
        self.entry_target_lat.insert(0, "52.2478")

        tk.Label(self.control_frame, text="Tryb transportu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.mode_vars = {}
        for mode in enums.RouteMode:
            row_frame = tk.Frame(self.control_frame)
            row_frame.pack(anchor="w", pady=2)
            color = self.mode_colors.get(mode, "#000000")
            color_box = tk.Canvas(row_frame, width=15, height=15, bg=color, highlightthickness=1, highlightbackground="black")
            color_box.pack(side="left", padx=(5, 5))

            if mode in [enums.RouteMode.WALK_PUBLIC, enums.RouteMode.WALK_PR]:
                lbl = tk.Label(row_frame, text=str(mode).upper())
                lbl.pack(side="left")
            else:
                var = tk.BooleanVar(value=True if mode == enums.RouteMode.CAR else False)
                chk = tk.Checkbutton(row_frame, text=str(mode).upper(), variable=var)
                chk.pack(side="left")
                self.mode_vars[mode] = var

        btn_calc = tk.Button(self.control_frame, text="Wyznacz trasę", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=self.calculate_and_draw)
        btn_calc.pack(fill="x", pady=(30, 0))

        self.results_frame = tk.Frame(self.control_frame)
        self.results_frame.pack(fill="x", pady=(20, 0))

    def _describe_route(self, nodes: list[tuple[float, float]], description: str, text_color: str = "black"):
        center_node = nodes[len(nodes) // 2]
        self.map_widget.set_marker(
            center_node[0],
            center_node[1],
            text=description,
            icon=tk.PhotoImage(width=1, height=1),
            text_color=text_color
        )

    def _draw_road_route(self, source: tuple[float, float], target: tuple[float, float]):
        route = routing.calculate_shortest_route_road(source=source, target=target)
        color = self.mode_colors.get(enums.RouteMode.CAR, "#000000")
        
        route.nodes = [(y, x) for x, y in route.nodes]
        self.map_widget.set_path(
            position_list=route.nodes,
            color=color,
            width=4
        )

        self._fit_bounding_box(nodes=route.nodes)
        return route

    def _draw_transit_route(self, source: tuple[float, float], target: tuple[float, float]):
        route = routing.calculate_shortest_route_transit(source=source, target=target)
        color = self.mode_colors.get(enums.RouteMode.PUBLIC, "#000000")
        all_nodes = []

        for segment in route.segments:
            segment.nodes = [(y, x) for x, y in segment.nodes]
            all_nodes.extend(segment.nodes)
            self.map_widget.set_path(
                position_list=segment.nodes,
                color=color if segment.line else self.mode_colors.get(enums.RouteMode.WALK_PUBLIC, "#000000"),
                width=4
            )
            if segment.line:
                self._describe_route(nodes=segment.nodes, description=segment.line, text_color="darkblue")

        self._fit_bounding_box(nodes=all_nodes)
        return route

    def _draw_pr_route(self, source: tuple[float, float], target: tuple[float, float], color: str | None = None):
        route = routing.calculate_shortest_route_pr(source=source, target=target)
        color = self.mode_colors.get(enums.RouteMode.PR, "#000000")
        all_nodes = []

        route.road_route.nodes = [(y, x) for x, y in route.road_route.nodes]
        all_nodes.extend(route.road_route.nodes)
        self.map_widget.set_path(
            position_list=route.road_route.nodes,
            color=color,
            width=4
        )

        self.map_widget.set_marker(route.pr_node[1], route.pr_node[0], text="PARKING", marker_color_circle="darkgray", marker_color_outside="black")

        for segment in route.transit_route.segments:
            segment.nodes = [(y, x) for x, y in segment.nodes]
            all_nodes.extend(segment.nodes)
            self.map_widget.set_path(
                position_list=segment.nodes,
                color=color if segment.line else self.mode_colors.get(enums.RouteMode.WALK_PR, "#000000"),
                width=4
            )
            if segment.line:
                self._describe_route(nodes=segment.nodes, description=segment.line, text_color="#4A148C")

        self._fit_bounding_box(nodes=all_nodes)
        return route

    def _fit_bounding_box(self, nodes: list[tuple[float, float]]):
        min_lat = min(node[0] for node in nodes)
        max_lat = max(node[0] for node in nodes)
        min_lon = min(node[1] for node in nodes)
        max_lon = max(node[1] for node in nodes)
        self.map_widget.fit_bounding_box((max_lat, min_lon), (min_lat, max_lon))

    def calculate_and_draw(self):
        """Pobiera dane, wywołuje 'algorytm' i rysuje trasę na mapie."""
        try:
            source = (float(self.entry_source_lon.get()), float(self.entry_source_lat.get()))
            target = (float(self.entry_target_lon.get()), float(self.entry_target_lat.get()))
        except ValueError:
            messagebox.showerror("Błąd danych", "Współrzędne muszą być liczbami zmiennoprzecinkowymi!")
            return

        selected_modes = [mode for mode, var in self.mode_vars.items() if var.get()]
        if not selected_modes:
            messagebox.showwarning("Brak trybu", "Wybierz przynajmniej jeden tryb transportu!")
            return

        self.map_widget.delete_all_path()
        self.map_widget.delete_all_marker()

        self.map_widget.set_marker(source[1], source[0], text="START", marker_color_circle="green", marker_color_outside="darkgreen")
        self.map_widget.set_marker(target[1], target[0], text="CEL", marker_color_circle="red", marker_color_outside="darkred")

        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        tk.Label(self.results_frame, text="Podsumowanie tras:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))

        draw_route_fn_map = {
            enums.RouteMode.CAR: self._draw_road_route,
            enums.RouteMode.PUBLIC: self._draw_transit_route,
            enums.RouteMode.PR: self._draw_pr_route
        }

        for mode in selected_modes:
            route = draw_route_fn_map[mode](source=source, target=target)

            row_frame = tk.Frame(self.results_frame)
            row_frame.pack(fill="x", pady=5)
            
            color = self.mode_colors.get(mode, "#000000")
            tk.Canvas(row_frame, width=15, height=15, bg=color, highlightthickness=1, highlightbackground="black").pack(side="left", padx=(0, 10))
            tk.Label(row_frame, text=str(mode).upper(), font=("Arial", 10)).pack(side="left")
            tk.Label(row_frame, text=f"{round(route.cost / 60)} min", font=("Arial", 10, "bold")).pack(side="right")


if __name__ == "__main__":
    root = tk.Tk()
    app = RoutingApp(root)
    root.mainloop()
