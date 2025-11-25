import subprocess
import shlex
import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import json
import traceback

# ---------------------------
# CONFIG
# Local Prolog file
PROLOG_FILE = r"C:\Users\Kukkinoba\Documents\polog-python\RoadNetworkKB.pl"

# Local swipl
SWIPL_CMD = r"C:\Program Files\swipl\bin\swipl.exe"


# SWISH API
SWISH_PENGINE_URL = "https://swish.swi-prolog.org/pengine/create"

# ---------------------------
def call_prolog_local(goal: str):
    """
    Call local swipl with the specified goal. Returns stdout string.
    """
    cmd = [SWIPL_CMD, "-q", "-s", PROLOG_FILE, "-g", goal, "-t", "halt"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("swipl not found. Set SWIPL_CMD to your swipl executable path or install SWI-Prolog.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Local Prolog timed out.")
    if proc.stderr:
        print("Prolog stderr:", proc.stderr)
    return proc.stdout.strip()

def call_prolog_online(goal: str):
    """
    Use SWISH pengine API: upload the prolog file content and ask goal.
    Returns the raw output string as emitted by run_query (if any).
    Notes: This uses the public SWISH endpoint.
    """
    if not os.path.exists(PROLOG_FILE):
        raise RuntimeError(f"Local PROLOG_FILE not found at {PROLOG_FILE} — required to upload program for remote execution.")
    prog = open(PROLOG_FILE, "r", encoding="utf8").read()

    payload = {
        "src": prog,
        "ask": goal,
        "format": "json"
    }

    try:
        resp = requests.post(SWISH_PENGINE_URL, json=payload, timeout=30)
    except Exception as e:
        raise RuntimeError("Online Prolog request failed: " + str(e))

    if resp.status_code != 201 and resp.status_code != 200:
        raise RuntimeError(f"SWISH responded with status {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError("Failed to parse SWISH JSON response: " + resp.text[:1000])


    def search_for_result(obj):
        if isinstance(obj, str):
            if "|" in obj and "[" in obj:
                return obj
            return None
        if isinstance(obj, dict):
            for k, v in obj.items():
                res = search_for_result(v)
                if res:
                    return res
        if isinstance(obj, list):
            for item in obj:
                res = search_for_result(item)
                if res:
                    return res
        return None

    result_text = search_for_result(data)
    if result_text:
        return result_text.strip()

    # As a fallback
    if 'events' in data:
        for ev in data['events']:
            if isinstance(ev, dict) and ev.get('output'):
                return ev['output'].strip()
            if isinstance(ev, dict) and ev.get('data'):
                rt = search_for_result(ev['data'])
                if rt:
                    return rt.strip()

    return json.dumps(data)[:2000]

def call_prolog(goal: str, use_online=False):
    if use_online:
        return call_prolog_online(goal)
    else:
        return call_prolog_local(goal)

# ---------------------------
# loading the grapgh from Prolog
EDGE_RE = re.compile(r"^E([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+)$")

def load_graph_from_prolog(use_online=False):
    out = call_prolog("export_edges.", use_online)
    G = nx.DiGraph()
    if not out:
        return G
    lines = []
    if isinstance(out, str):
        for ln in out.splitlines():
            ln2 = ln.strip()
            if ln2.startswith("E"):
                lines.append(ln2)
    for line in lines:
        m = EDGE_RE.match(line.strip())
        if not m:
            continue
        a,b,d,t,time,status = m.groups()
        a = a.strip()
        b = b.strip()
        try:
            d_val = float(d)
            time_val = float(time)
        except:
            d_val = 0.0
            time_val = 0.0
        G.add_node(a)
        G.add_node(b)
        G.add_edge(a, b, distance=d_val, rtype=t, time=time_val, status=status)
    return G

# format user input
def to_atom(s: str) -> str:
    s2 = re.sub(r'[^a-z0-9_ ]', '', s.lower())
    s2 = s2.replace(' ', '_')
    if not s2:
        s2 = 'unknown'
    return s2

# Calling the run_query
def find_route_prolog(criteria_atom, start_atom, goal_atom, use_online=False):
    goal = f"run_query({criteria_atom},{start_atom},{goal_atom})"
    out = call_prolog(goal, use_online=use_online)
    if not out:
        return None
    m = re.search(r"(\[[^\]]+\]\|\s*-?\d+(\.\d+)?\|\s*-?\d+(\.\d+)?)", out)
    if not m:
        print("DEBUG: Could not parse prolog output. Raw:", out[:1000])
        return None
    s = m.group(1)
    try:
        path_str, dist_str, time_str = s.split("|")
        path_str = path_str.strip()
        if path_str.startswith("[") and path_str.endswith("]"):
            inner = path_str[1:-1].strip()
            if inner == "":
                path = []
            else:
                path = [p.strip() for p in inner.split(",")]
        else:
            path = [path_str]
        dist = float(dist_str)
        ttime = float(time_str)
        return path, dist, ttime
    except Exception as e:
        print("Failed to parse parsed match:", e)
        print("Raw match:", s)
        return None

# locally add news roads
def append_road_to_file(src_atom, dst_atom, distance_val, rtype_atom, time_val, status_atom):
    fact = f"road({src_atom}, {dst_atom}, {distance_val}, {rtype_atom}, {time_val}, {status_atom}).\n"
    with open(PROLOG_FILE, "a", encoding="utf-8") as f:
        f.write(fact)

# ---------------------------
# GUI part
class PathFinderApp:
    def __init__(self, root):
        self.root = root
        root.title("Clarendon Path Finder (Python + Prolog) - Local/Online")
        root.geometry("1000x720")

        top = ttk.Label(root, text="Clarendon Rural Road Network — Path Finder", font=("Arial", 16))
        top.pack(pady=6)

        controls = ttk.Frame(root)
        controls.pack(fill="x", padx=12)

        # Mode
        ttk.Label(controls, text="Prolog Mode:").grid(row=0, column=0, padx=5, pady=4, sticky="e")
        self.mode_var = tk.StringVar(value="local")
        mode_frame = ttk.Frame(controls)
        mode_frame.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ttk.Radiobutton(mode_frame, text="Local", variable=self.mode_var, value="local").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Online (SWISH)", variable=self.mode_var, value="online").pack(side="left")

        ttk.Label(controls, text="swipl path (optional):").grid(row=0, column=2, padx=5, pady=4, sticky="e")
        self.swipl_entry = ttk.Entry(controls, width=40)
        self.swipl_entry.grid(row=0, column=3, padx=5, pady=4)
        self.swipl_entry.insert(0, SWIPL_CMD)

        # goal selection
        ttk.Label(controls, text="Start:").grid(row=1, column=0, padx=5, pady=6, sticky="e")
        self.start_cb = ttk.Combobox(controls, values=[], width=28)
        self.start_cb.grid(row=1, column=1, padx=5, pady=6)

        ttk.Label(controls, text="Goal:").grid(row=1, column=2, padx=5, pady=6, sticky="e")
        self.goal_cb = ttk.Combobox(controls, values=[], width=28)
        self.goal_cb.grid(row=1, column=3, padx=5, pady=6)

        ttk.Label(controls, text="Criteria:").grid(row=2, column=0, padx=5, pady=6, sticky="e")
        self.criteria_cb = ttk.Combobox(controls, state="readonly", width=40,
                                        values=["Shortest Distance", "Fastest Time",
                                                "Avoid Unpaved Roads", "Avoid Broken Cistern Roads",
                                                "Avoid Deep Potholes", "Loose Constraints (BFS)"])
        self.criteria_cb.current(0)
        self.criteria_cb.grid(row=2, column=1, padx=5, pady=6, sticky="w")

        ttk.Button(controls, text="Find Path", command=self.find_path).grid(row=2, column=2, padx=8, pady=6)
        ttk.Button(controls, text="Refresh Map", command=self.refresh_map).grid(row=2, column=3, padx=8, pady=6)

        # map
        bottom = ttk.Frame(root)
        bottom.pack(fill="both", expand=True, padx=12, pady=12)

        # results
        left = ttk.LabelFrame(bottom, text="Results", width=360)
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.result_text = tk.Text(left, width=45, height=24, wrap="word")
        self.result_text.pack(padx=6, pady=6)

        # map canvas
        right = ttk.LabelFrame(bottom, text="Map")
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.fig, self.ax = plt.subplots(figsize=(6,5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # admin controls
        admin = ttk.LabelFrame(root, text="Administrator (Add / Update Road) - appends to local roads.pl")
        admin.pack(fill="x", padx=12, pady=6)

        arow = 0
        ttk.Label(admin, text="Source:").grid(row=arow, column=0, sticky="e", padx=4, pady=3)
        self.admin_src = ttk.Entry(admin, width=20)
        self.admin_src.grid(row=arow, column=1, padx=4, pady=3)
        ttk.Label(admin, text="Destination:").grid(row=arow, column=2, sticky="e", padx=4, pady=3)
        self.admin_dst = ttk.Entry(admin, width=20)
        self.admin_dst.grid(row=arow, column=3, padx=4, pady=3)

        arow += 1
        ttk.Label(admin, text="Distance (km):").grid(row=arow, column=0, sticky="e", padx=4, pady=3)
        self.admin_dist = ttk.Entry(admin, width=12)
        self.admin_dist.grid(row=arow, column=1, padx=4, pady=3)
        ttk.Label(admin, text="Time (min):").grid(row=arow, column=2, sticky="e", padx=4, pady=3)
        self.admin_time = ttk.Entry(admin, width=12)
        self.admin_time.grid(row=arow, column=3, padx=4, pady=3)

        arow += 1
        ttk.Label(admin, text="Type:").grid(row=arow, column=0, sticky="e", padx=4, pady=3)
        self.admin_type = ttk.Combobox(admin, values=["paved","unpaved","broken_cisterns","deep_potholes"], width=18)
        self.admin_type.grid(row=arow, column=1, padx=4, pady=3)
        ttk.Label(admin, text="Status:").grid(row=arow, column=2, sticky="e", padx=4, pady=3)
        self.admin_status = ttk.Combobox(admin, values=["open","closed"], width=18)
        self.admin_status.grid(row=arow, column=3, padx=4, pady=3)

        arow += 1
        ttk.Button(admin, text="Add / Persist Road", command=self.admin_add_road).grid(row=arow, column=1, pady=6)
        ttk.Button(admin, text="Rebuild Nodes List", command=self.refresh_nodes_list).grid(row=arow, column=3, pady=6)

        self.G = nx.DiGraph()
        try:
            self.refresh_map()
            self.refresh_nodes_list()
        except Exception as e:
            messagebox.showerror("Startup error", str(e))

    # -----------------------
    def get_use_online_flag(self):
        return self.mode_var.get() == "online"

    def refresh_map(self):
        global SWIPL_CMD
        SWIPL_CMD = self.swipl_entry.get().strip() or SWIPL_CMD

        try:
            self.G = load_graph_from_prolog(use_online=self.get_use_online_flag())
            self.draw_graph(self.G)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error loading graph", str(e))

    def refresh_nodes_list(self):
        nodes = sorted(self.G.nodes())
        self.start_cb['values'] = nodes
        self.goal_cb['values'] = nodes

    def draw_graph(self, G, highlight_path=None):
        self.ax.clear()
        if len(G) == 0:
            self.ax.text(0.5,0.5,"No graph data found.\nUse Admin to add roads (local) or switch mode to Local/Online.",ha="center",va="center")
            self.canvas.draw()
            return
        pos = nx.spring_layout(G, seed=42)
        nx.draw_networkx_nodes(G, pos, ax=self.ax, node_size=360)
        nx.draw_networkx_labels(G, pos, ax=self.ax, font_size=9)
        # edges coloring
        edge_colors = []
        for u,v,data in G.edges(data=True):
            if data.get('status') == 'closed':
                edge_colors.append('red')
            elif data.get('rtype') == 'unpaved':
                edge_colors.append('orange')
            else:
                edge_colors.append('black')
        nx.draw_networkx_edges(G, pos, ax=self.ax, edge_color=edge_colors, arrows=True)
        edge_labels = { (u,v): f"{int(data.get('distance',0))}km" for u,v,data in G.edges(data=True) }
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

        # highlight the path
        if highlight_path and len(highlight_path) >= 2:
            path_edges = []
            for a,b in zip(highlight_path, highlight_path[1:]):
                if (a,b) in G.edges():
                    path_edges.append((a,b))
            if path_edges:
                nx.draw_networkx_edges(G, pos, edgelist=path_edges, width=3.0, edge_color='green', ax=self.ax)

        self.ax.set_axis_off()
        self.canvas.draw()

    # -----------------------
    def find_path(self):
        start_raw = self.start_cb.get().strip()
        goal_raw = self.goal_cb.get().strip()
        criteria_raw = self.criteria_cb.get().strip()

        if not start_raw or not goal_raw:
            messagebox.showwarning("Input missing", "Select start and goal nodes.")
            return

        mapping = {
            "Shortest Distance": "shortest_distance",
            "Fastest Time": "fastest_time",
            "Avoid Unpaved Roads": "avoid_unpaved",
            "Avoid Broken Cistern Roads": "avoid_broken",
            "Avoid Deep Potholes": "avoid_deep_potholes",
            "Loose Constraints (BFS)": "loose_constraints"
        }
        crit_atom = mapping.get(criteria_raw, "shortest_distance")
        start_atom = to_atom(start_raw)
        goal_atom = to_atom(goal_raw)
        use_online = self.get_use_online_flag()

        self.result_text.delete("1.0", tk.END)
        try:
            res = find_route_prolog(crit_atom, start_atom, goal_atom, use_online=use_online)
        except Exception as e:
            traceback.print_exc()
            self.result_text.insert(tk.END, f"Error when calling Prolog: {e}\n")
            return

        if not res:
            self.result_text.insert(tk.END, "⚠️ No path found or Prolog returned no output.\n")
            self.draw_graph(self.G, highlight_path=None)
            return

        path, dist, ttime = res
        self.result_text.insert(tk.END, f"Route: {' -> '.join(path)}\n")
        self.result_text.insert(tk.END, f"Total distance: {dist:.2f} km\n")
        self.result_text.insert(tk.END, f"Estimated time: {ttime:.2f} minutes\n")

        # highlight it on the map
        self.draw_graph(self.G, highlight_path=path)

    # -----------------------
    def admin_add_road(self):
        src = self.admin_src.get().strip()
        dst = self.admin_dst.get().strip()
        d = self.admin_dist.get().strip()
        t = self.admin_time.get().strip()
        rtype = self.admin_type.get().strip()
        status = self.admin_status.get().strip()

        if not (src and dst and d):
            messagebox.showerror("Missing", "Please fill source, destination, and distance.")
            return
        try:
            dval = float(d)
        except:
            messagebox.showerror("Invalid", "Distance must be numeric.")
            return
        try:
            tval = float(t) if t else 0.0
        except:
            tval = 0.0

        src_atom = to_atom(src)
        dst_atom = to_atom(dst)
        rtype_atom = to_atom(rtype) if rtype else "paved"
        status_atom = to_atom(status) if status else "open"

        # Append to roads.pl
        try:
            append_road_to_file(src_atom, dst_atom, dval, rtype_atom, tval, status_atom)
            messagebox.showinfo("Saved", f"Road appended to {PROLOG_FILE}.\nClick Refresh Map to load it.")
        except Exception as e:
            messagebox.showerror("Failed to append fact", str(e))
        # reload the graph in the UI
        self.refresh_map()
        self.refresh_nodes_list()

# ---------------------------
# MAIN fonction
# ---------------------------
if __name__ == "__main__":
    missing = []
    try:
        import requests 
    except Exception:
        missing.append("requests")

    if missing:
        messagebox.showerror("Missing libraries", "Install required packages: pip install networkx matplotlib requests")
    root = tk.Tk()
    app = PathFinderApp(root)
    root.mainloop()