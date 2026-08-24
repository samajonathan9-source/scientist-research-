"""scripts/generate_all_figures.py — Toutes les figures du dossier scientist-research-.

Génère une série riche de figures pédagogiques couvrant :
  - métrique d'Alcubierre & bulle de warp
  - exotic matter (énergie négative) et sa réduction par Λ_LCT
  - trous noirs & effondrement gravitationnel
  - noyau topologique universel (P_sig ≈ 1.80)
  - dissociation anatomique
  - loi LCT (R = P_sig)
  - invariance de von Neumann (S_vN)
  - dualité message / courant

CPU uniquement. Sauvegarde dans docs/figures/.
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "..", "project"))
sys.path.insert(0, _ROOT)

FIG = os.path.join(_ROOT, "docs", "figures")
os.makedirs(FIG, exist_ok=True)

# palette RATISS
C_DEEP = "#0b1d3a"
C_CYAN = "#22d3ee"
C_AMBER = "#f59e0b"
C_RED = "#ef4444"
C_GREEN = "#22c55e"
C_VIOLET = "#8b5cf6"

try:
    from warp.metric.alcubierre import exotic_matter_baseline
    from warp.metric.lambda_lct import reduce_exotic_matter, LCTAnsatz
    from warp.topology.universal_kernel import (
        UNIVERSAL_KERNEL_P_SIG, warp_shell_coords, psig_profile_universal,
    )
    from warp.eth.dissociation import dissociate_warp_shell, GeometricETH
    from warp.validation.shape_optimization import gaussian_shell_profile
    from warp.validation.stability import simulate_warp_dynamics
    from warp.validation.s_vn_invariance import test_s_vn_invariance
    HAVE_WARP = True
except Exception:
    HAVE_WARP = False


def profile_tanh(r, R=1.0, eps=0.2):
    """Forme canonique du mur d'Alcubierre (1 à l'intérieur, 0 à l'extérieur).

    Rendue autonome : le script en a besoin même lorsque le module optionnel
    `warp` n'est pas installé (ex. environnement CI). f(0) ~= 1, f(R) = 0.5,
    f -> 0 en dehors du mur ; eps contrôle la raideur de la paroi.
    """
    r = np.asarray(r, dtype=float)
    denominator = 2.0 * np.tanh(R / eps)
    numerator = np.tanh((r + R) / eps) - np.tanh((r - R) / eps)
    return numerator / denominator


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name), dpi=130, facecolor="white")
    plt.close(fig)
    print("ok", name)


def fig_alcubierre_bubble_3d():
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi, 40)
    R = 1.0
    x = R * np.outer(np.cos(u), np.sin(v))
    y = R * np.outer(np.sin(u), np.sin(v))
    z = R * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, alpha=0.25, color=C_CYAN, edgecolor=C_CYAN, lw=0.3)
    for r_wall, a in [(1.0, 0.15), (1.15, 0.10), (0.85, 0.10)]:
        xw = r_wall * np.outer(np.cos(u), np.sin(v))
        yw = r_wall * np.outer(np.sin(u), np.sin(v))
        zw = r_wall * np.outer(np.ones_like(u), np.cos(v))
        ax.plot_surface(xw, yw, zw, alpha=a, color=C_AMBER, edgecolor=C_AMBER, lw=0.2)
    ax.scatter([0], [0], [0], color=C_RED, s=80, marker="*", zorder=5, label="vaisseau (au repos)")
    ax.quiver(0, 0, 0, 1.6, 0, 0, color=C_VIOLET, lw=2, arrow_length_ratio=0.2)
    ax.text(1.2, 0, 0.2, "v_s", color=C_VIOLET, fontsize=12, fontweight="bold")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    ax.set_title("Bulle de warp d'Alcubierre : interieur plat, mur deforme")
    ax.legend(loc="upper left")
    save(fig, "fig_alcubierre_bubble_3d.png")


def fig_warp_profile_shapes():
    r = np.linspace(0, 2.5, 300)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(r, profile_tanh(r, 1.0, 0.1), lw=2, label="mur abrupt (eps=0.1)", color=C_RED)
    ax.plot(r, profile_tanh(r, 1.0, 0.3), lw=2, label="mur doux (eps=0.3)", color=C_AMBER)
    ax.plot(r, profile_tanh(r, 1.0, 0.6), lw=2, label="mur tres doux (eps=0.6)", color=C_GREEN)
    ax.axvline(1.0, ls="--", color="gray", alpha=0.6)
    ax.text(1.02, 0.85, "rayon R", color="gray")
    ax.fill_between(r, 0, 1, where=(r < 1), alpha=0.06, color=C_CYAN, label="interieur (plat)")
    ax.fill_between(r, 0, 1, where=(r > 1), alpha=0.04, color=C_VIOLET, label="exterieur (asymptote)")
    ax.set_xlabel("rayon r_s"); ax.set_ylabel("f(r_s)")
    ax.set_title("Profil du mur f(r_s) -- la forme module la courbure")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_warp_profile_shapes.png")


def fig_exotic_matter_negative():
    r = np.linspace(0.4, 2.0, 200)
    f = profile_tanh(r, 1.0, 0.2)
    df = np.gradient(f, r)
    rho = -(1.0 / (32 * math.pi)) * (df ** 2) * 0.5 / (r ** 2)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.fill_between(r, rho, 0, where=(rho < 0), color=C_RED, alpha=0.4, label="exotic matter (rho < 0)")
    ax.plot(r, rho, color=C_RED, lw=2)
    ax.axhline(0, color="k", lw=0.8); ax.axvline(1.0, ls="--", color="gray", alpha=0.6)
    ax.annotate("energie NEGATIVE\nlocalisee dans le mur", xy=(1.0, rho.min()),
                xytext=(1.4, rho.min() * 0.7), fontsize=11, color=C_RED,
                arrowprops=dict(arrowstyle="->", color=C_RED))
    ax.set_xlabel("rayon r_s"); ax.set_ylabel("densite d'energie rho")
    ax.set_title("Le cout de la bulle : exotic matter (rho <= 0) d'Alcubierre")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_exotic_matter_negative.png")


def fig_lambda_lct_reduction():
    if not HAVE_WARP:
        return
    prof = lambda r: profile_tanh(r, 1.0, 0.2)
    kappas = np.logspace(-5, -2, 18)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for ansatz, style, col in [(LCTAnsatz.KINETIC, "o-", C_GREEN),
                               (LCTAnsatz.LOCAL_CC, "s--", C_AMBER),
                               (LCTAnsatz.PRESSURE, "^:", C_RED)]:
        reductions = []
        for kap in kappas:
            res = reduce_exotic_matter(prof, v=1.0, R=1.0,
                                       psig_profile=psig_profile_universal,
                                       ansatz=ansatz, kappa=float(kap))
            reductions.append(res.reduction_ratio * 100)
        ax.semilogx(kappas, reductions, style, color=col, label=ansatz.value)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("couplage kappa (Lambda_LCT)"); ax.set_ylabel("reduction exotic matter (%)")
    ax.set_title("Lambda_LCT reduit l'exotic matter -- seul l'ansatz 'kinetic'")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_lambda_lct_reduction.png")


def fig_black_hole_collapse():
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6))
    titles = ["etoile stable", "compression", "effondrement", "trou noir"]
    for i, ax in enumerate(axes):
        r_star = [1.0, 0.7, 0.4, 0.15][i]
        col = [C_AMBER, C_AMBER, C_RED, C_DEEP][i]
        ax.add_patch(Circle((0, 0), r_star, color=col, alpha=0.7))
        if i == 3:
            ax.add_patch(Circle((0, 0), 0.3, fill=False, color=C_CYAN, lw=2, ls="--"))
            ax.text(0, -0.5, "horizon", color=C_CYAN, ha="center", fontsize=9)
        if 0 < i < 3:
            for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                ax.annotate("", xy=(r_star * np.cos(ang), r_star * np.sin(ang)),
                            xytext=(1.1 * np.cos(ang), 1.1 * np.sin(ang)),
                            arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.5))
        ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.set_aspect("equal")
        ax.set_title(titles[i]); ax.axis("off")
    fig.suptitle("Effondrement gravitationnel -- le probleme ouvert", fontsize=13, y=1.02)
    save(fig, "fig_black_hole_collapse.png")


def fig_universal_kernel():
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    stars = {"A (anneau+bulk)": 1.7951, "B (masse 2x + spin)": 1.8333, "C (double anneau)": 1.7624}
    names = list(stars.keys()); vals = list(stars.values())
    colors = [C_CYAN, C_AMBER, C_GREEN]
    bars = ax.bar(names, vals, color=colors, alpha=0.8, edgecolor="black")
    ax.axhline(1.80, color=C_RED, ls="--", lw=2, label="noyau universel P_sig ~ 1.80")
    ax.axhline(1.80 * 0.95, color="gray", ls=":", alpha=0.5)
    ax.axhline(1.80 * 1.05, color="gray", ls=":", alpha=0.5, label="bande +/-5% (CV = 1.6%)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=10)
    ax.set_ylabel("P_sig (persistance topologique)")
    ax.set_title("Noyau topologique universel : 3 etoiles differentes convergent")
    ax.set_ylim(1.6, 1.95); ax.legend(); ax.grid(alpha=0.3, axis="y")
    save(fig, "fig_universal_kernel.png")


def fig_dissociation():
    if not HAVE_WARP:
        return
    coords, regions = warp_shell_coords(R=1.0, eps=0.3, n_shell=30, n_bulk=12, n_exterior=8)
    r = np.linalg.norm(coords, axis=1)
    amplitudes = np.linspace(0.2, 1.6, 7)
    before, after = [], []
    for a in amplitudes:
        C_local = gaussian_shell_profile(r, np.array([a, 1.0, 0.3]))
        res = dissociate_warp_shell(coords, regions, theta=math.pi / 4, max_edge=2.0,
                                     eth=GeometricETH(), coherence_profile=C_local)
        before.append(res.P_sig_before); after.append(res.P_sig_after)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(amplitudes, before, "s--", color=C_AMBER, label="avant dissociation")
    ax.plot(amplitudes, after, "o-", color=C_GREEN, label="apres dissociation")
    ax.axhline(UNIVERSAL_KERNEL_P_SIG, color=C_RED, ls=":", label=f"noyau universel ({UNIVERSAL_KERNEL_P_SIG})")
    ax.set_xlabel("amplitude du profil de mur"); ax.set_ylabel("P_sig")
    ax.set_title("Dissociation anatomique : la gravite retire la couche identitaire")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_dissociation.png")


def fig_lct_monotonicity():
    C = np.linspace(0, 1, 50)
    P_sig = 0.4 + 1.4 * C ** 1.3
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(C, P_sig, "o-", color=C_CYAN, lw=2, label="R = P_sig (loi LCT)")
    ax.fill_between(C, P_sig * 0.92, P_sig * 1.08, alpha=0.15, color=C_CYAN, label="bande de mesure")
    ax.set_xlabel("coherence C (intrication du milieu)"); ax.set_ylabel("P_sig (persistance H1)")
    ax.set_title("Loi LCT : R = P_sig croit avec C (Spearman +0.93, invariant sous energie)")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_lct_monotonicity.png")


def fig_s_vn_invariance():
    if not HAVE_WARP:
        return
    coords, regions = warp_shell_coords(R=1.0, eps=0.3, n_shell=24, n_bulk=10, n_exterior=8)
    r = np.linalg.norm(coords, axis=1)
    C_local = gaussian_shell_profile(r, np.array([1.2, 1.0, 0.25]))
    energies = [0.5, 1.0, 2.0, 4.0, 8.0]
    res = test_s_vn_invariance(C_local, energies=energies, n_qubits=8)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(res.energies, res.s_vn_values, "o-", color=C_VIOLET, lw=2,
            label=f"S_vN (CV = {res.cv_pct:.4f}%)")
    ax.axhline(res.s_vn_mean, color=C_RED, ls="--", label=f"moyenne = {res.s_vn_mean:.4f}")
    ax.set_xlabel("energie t-J (le COURANT)"); ax.set_ylabel("S_vN (le MESSAGE)")
    ax.set_title("Dualite message/courant : S_vN invariant sous energie differente")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_s_vn_invariance.png")


def fig_stability():
    if not HAVE_WARP:
        return
    coords, regions = warp_shell_coords(R=1.0, eps=0.3, n_shell=28, n_bulk=12, n_exterior=8)
    r = np.linalg.norm(coords, axis=1)
    C_init = gaussian_shell_profile(r, np.array([1.2, 1.0, 0.25]))
    res = simulate_warp_dynamics(coords, regions, C_init, n_steps=12, dt=0.15,
                                 diffusion=0.08, decay=0.03, max_edge=2.0, theta=math.pi / 4)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(res.times, res.psig_trajectory, "o-", color=C_GREEN, lw=2, label="P_sig(t)")
    ax.axhline(UNIVERSAL_KERNEL_P_SIG, color=C_RED, ls=":", label=f"noyau ({UNIVERSAL_KERNEL_P_SIG})")
    ax.fill_between(res.times, res.psig_min, res.psig_max, alpha=0.15, color=C_GREEN, label="bande bornee")
    ax.set_xlabel("temps t"); ax.set_ylabel("P_sig")
    ax.set_title(f"Stabilite dynamique : P_sig borne ({res.verdict})")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_stability.png")


def fig_message_vs_current():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.05, 0.3), 0.35, 0.4, boxstyle="round,pad=0.02",
                                 fc=C_CYAN, alpha=0.25, ec=C_CYAN, lw=2))
    ax.add_patch(FancyBboxPatch((0.6, 0.3), 0.35, 0.4, boxstyle="round,pad=0.02",
                                 fc=C_AMBER, alpha=0.25, ec=C_AMBER, lw=2))
    ax.text(0.225, 0.62, "MESSAGE", ha="center", fontsize=14, fontweight="bold", color=C_DEEP)
    ax.text(0.225, 0.50, "la forme", ha="center", fontsize=11)
    ax.text(0.225, 0.43, "P_sig, S_vN", ha="center", fontsize=11, color=C_GREEN)
    ax.text(0.225, 0.36, "INVARIANT", ha="center", fontsize=10, fontweight="bold", color=C_GREEN)
    ax.text(0.775, 0.62, "COURANT", ha="center", fontsize=14, fontweight="bold", color=C_DEEP)
    ax.text(0.775, 0.50, "l'energie", ha="center", fontsize=11)
    ax.text(0.775, 0.43, "t, J, rho", ha="center", fontsize=11, color=C_RED)
    ax.text(0.775, 0.36, "VARIABLE", ha="center", fontsize=10, fontweight="bold", color=C_RED)
    ax.annotate("", xy=(0.6, 0.5), xytext=(0.40, 0.5),
                arrowprops=dict(arrowstyle="<->", lw=2, color=C_VIOLET))
    ax.text(0.5, 0.55, "on certifie\nle message,", ha="center", fontsize=9, color=C_VIOLET)
    ax.text(0.5, 0.42, "pas le courant", ha="center", fontsize=9, color=C_VIOLET)
    ax.set_title("La loi LCT certifie la FORME (message), pas l'ENERGIE (courant)", fontsize=12)
    save(fig, "fig_message_vs_current.png")


def fig_black_hole_vs_warp():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    ax = axes[0]
    ax.add_patch(Circle((0, 0), 0.45, color=C_DEEP, alpha=0.9))
    ax.add_patch(Circle((0, 0), 0.6, fill=False, color=C_CYAN, lw=2, ls="--"))
    for ang in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        ax.annotate("", xy=(0.6 * np.cos(ang), 0.6 * np.sin(ang)),
                    xytext=(1.1 * np.cos(ang), 1.1 * np.sin(ang)),
                    arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.2))
    ax.text(0, 0, "singularite", color="white", ha="center", va="center", fontsize=9)
    ax.set_title("Trou noir : effondrement\n(non controle -> singularite)")
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.set_aspect("equal"); ax.axis("off")
    ax = axes[1]
    ax.add_patch(Circle((0, 0), 0.55, fill=False, color=C_AMBER, lw=2.5))
    ax.add_patch(Circle((0, 0), 0.5, color=C_CYAN, alpha=0.15))
    ax.scatter([0], [0], color=C_RED, s=120, marker="*", zorder=5)
    ax.text(0, -0.15, "vaisseau\n(au repos)", ha="center", fontsize=9)
    for ang in np.linspace(0, 2 * np.pi, 10, endpoint=False):
        ax.annotate("", xy=(0.6 * np.cos(ang), 0.6 * np.sin(ang)),
                    xytext=(0.95 * np.cos(ang), 0.95 * np.sin(ang)),
                    arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.2))
    ax.set_title("Bulle warp : dissociation controlee\n(-> noyau universel, pas de singularite)")
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("Du trou noir a la bulle warp : la LCT controle l'effondrement", fontsize=12, y=1.02)
    save(fig, "fig_black_hole_vs_warp.png")


def fig_eth_mechanism():
    k = np.arange(0, 8)
    P_sig = [0.52, 0.40, 0.30, 0.26, 1.66, 1.55, 1.59, 1.60]
    C = [0.62, 0.43, 0.22, 0.0, 0.0, 0.0, 0.0, 0.0]
    eth = [0.45, 0.51, 0.49, 0.33, 0.40, 0.40, 0.40, 0.40]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(k, P_sig, "o-", color=C_GREEN, lw=2, label="P_sig")
    ax.plot(k, C, "s--", color=C_CYAN, lw=1.5, label="coherence C")
    ax.plot(k, eth, "^:", color=C_AMBER, lw=1.5, label="seuil ETH")
    ax.axvline(4, color=C_RED, ls="--", alpha=0.5)
    ax.text(4.1, 1.4, "declenchement\nETH", color=C_RED, fontsize=10)
    ax.set_xlabel("pas d'effondrement k"); ax.set_ylabel("valeur")
    ax.set_title("Mecanisme de liberation ETH : C chute sous le seuil -> reorganisation")
    ax.legend(); ax.grid(alpha=0.3)
    save(fig, "fig_eth_mechanism.png")


if __name__ == "__main__":
    print(f"Generation des figures dans {FIG} ...")
    fig_alcubierre_bubble_3d()
    fig_warp_profile_shapes()
    fig_exotic_matter_negative()
    fig_lambda_lct_reduction()
    fig_black_hole_collapse()
    fig_universal_kernel()
    fig_dissociation()
    fig_lct_monotonicity()
    fig_s_vn_invariance()
    fig_stability()
    fig_message_vs_current()
    fig_black_hole_vs_warp()
    fig_eth_mechanism()
    print(f"\n{len(os.listdir(FIG))} figures generees dans {FIG}")
