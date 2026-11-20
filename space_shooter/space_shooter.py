"""
Petit jeu de tir spatial façon "arcade des années 80" (inspiré du genre Galaga).

Contrôles :
    Flèches gauche/droite (ou A / D) : déplacer le vaisseau
    Espace                            : tirer
    P                                 : pause
    Entrée                            : (re)commencer une partie
    Échap                             : quitter

Dépendance : pygame  (pip install pygame)
"""

import math
import random

import pygame

# --------------------------------------------------------------------------
# Paramètres généraux
# --------------------------------------------------------------------------
LARGEUR, HAUTEUR = 480, 640
FPS = 60

NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
CYAN = (0, 220, 255)
JAUNE = (255, 220, 0)
ROUGE = (255, 60, 60)
VERT = (60, 255, 120)
VIOLET = (200, 80, 255)
ORANGE = (255, 150, 30)

VITESSE_JOUEUR = 5
VITESSE_TIR = 9
MAX_TIRS_JOUEUR = 2          # comme en arcade : 2 tirs à l'écran maximum
VITESSE_TIR_ENNEMI = 4
VIES_DEPART = 3


# --------------------------------------------------------------------------
# Fond étoilé défilant
# --------------------------------------------------------------------------
class Etoiles:
    def __init__(self, nombre=70):
        self.etoiles = [
            [random.randrange(LARGEUR), random.randrange(HAUTEUR), random.choice((1, 2, 3))]
            for _ in range(nombre)
        ]

    def update(self):
        for e in self.etoiles:
            e[1] += e[2]
            if e[1] > HAUTEUR:
                e[0], e[1] = random.randrange(LARGEUR), 0

    def draw(self, ecran):
        for x, y, v in self.etoiles:
            couleur = (80 * v, 80 * v, 80 * v)
            ecran.fill(couleur, (x, y, 2 if v == 3 else 1, 2 if v == 3 else 1))


# --------------------------------------------------------------------------
# Joueur
# --------------------------------------------------------------------------
class Joueur:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 30, 24)
        self.reset()

    def reset(self):
        self.rect.midbottom = (LARGEUR // 2, HAUTEUR - 20)
        self.invincible = 120  # frames d'invincibilité après réapparition

    def update(self, touches):
        if touches[pygame.K_LEFT] or touches[pygame.K_a]:
            self.rect.x -= VITESSE_JOUEUR
        if touches[pygame.K_RIGHT] or touches[pygame.K_d]:
            self.rect.x += VITESSE_JOUEUR
        self.rect.clamp_ip(pygame.Rect(0, 0, LARGEUR, HAUTEUR))
        if self.invincible > 0:
            self.invincible -= 1

    def draw(self, ecran):
        # Clignote quand il est invincible
        if self.invincible and (self.invincible // 6) % 2:
            return
        dessiner_vaisseau(ecran, self.rect.centerx, self.rect.centery, 1.0)


def dessiner_vaisseau(ecran, cx, cy, echelle):
    s = echelle
    corps = [(cx, cy - 12 * s), (cx + 6 * s, cy + 4 * s), (cx - 6 * s, cy + 4 * s)]
    aile_g = [(cx - 4 * s, cy), (cx - 15 * s, cy + 12 * s), (cx - 4 * s, cy + 8 * s)]
    aile_d = [(cx + 4 * s, cy), (cx + 15 * s, cy + 12 * s), (cx + 4 * s, cy + 8 * s)]
    pygame.draw.polygon(ecran, BLANC, corps)
    pygame.draw.polygon(ecran, ROUGE, aile_g)
    pygame.draw.polygon(ecran, ROUGE, aile_d)
    pygame.draw.circle(ecran, CYAN, (int(cx), int(cy - 2 * s)), max(1, int(3 * s)))


# --------------------------------------------------------------------------
# Ennemis
# --------------------------------------------------------------------------
# Trois types : (couleur principale, couleur ailes, points en formation, points en piqué)
TYPES_ENNEMIS = {
    "boss":   (VERT, VIOLET, 150, 400),
    "papillon": (ROUGE, BLANC, 80, 160),
    "abeille": (JAUNE, CYAN, 50, 100),
}


class Ennemi:
    FORMATION, PIQUE, RETOUR = range(3)

    def __init__(self, type_, col, ligne, niveau):
        self.type = type_
        self.col, self.ligne = col, ligne
        self.etat = Ennemi.FORMATION
        self.x, self.y = self.position_formation(0)
        # Entrée en scène : chaque ennemi arrive depuis le haut avec un léger délai
        self.y -= HAUTEUR
        self.rect = pygame.Rect(0, 0, 26, 20)
        self.pv = 2 if type_ == "boss" else 1
        self.t = 0.0
        self.vitesse_pique = 3 + niveau * 0.4
        self.vx = 0.0
        self.tir_cooldown = 0

    def position_formation(self, balancement):
        x = 60 + self.col * 40 + balancement
        y = 70 + self.ligne * 36
        return x, y

    def lancer_pique(self, cible_x):
        self.etat = Ennemi.PIQUE
        self.t = 0.0
        self.cible_x = cible_x
        self.sens = -1 if self.x > LARGEUR / 2 else 1
        self.tir_cooldown = random.randint(20, 50)

    def update(self, balancement, joueur, tirs_ennemis, niveau):
        fx, fy = self.position_formation(balancement)
        if self.etat == Ennemi.FORMATION:
            # Glisse doucement vers sa place dans la formation
            self.x += (fx - self.x) * 0.08
            self.y += (fy - self.y) * 0.08
        elif self.etat == Ennemi.PIQUE:
            self.t += 1
            # Petit looping au début, puis descente en serpentant vers le joueur
            if self.t < 40:
                angle = self.t / 40 * math.pi
                self.x += math.cos(angle) * 3 * self.sens
                self.y -= math.sin(angle) * 2.5
            else:
                cible = joueur.rect.centerx if self.y < HAUTEUR - 150 else self.x
                self.vx += (cible - self.x) * 0.002
                self.vx = max(-3, min(3, self.vx))
                self.x += self.vx + math.sin(self.t / 10) * 1.5
                self.y += self.vitesse_pique
                self.tir_cooldown -= 1
                if self.tir_cooldown <= 0 and self.y < HAUTEUR - 200:
                    tirs_ennemis.append(TirEnnemi(self.x, self.y + 10, joueur.rect.centerx))
                    self.tir_cooldown = max(30, 90 - niveau * 8)
            if self.y > HAUTEUR + 30:
                # Sort par le bas, réapparaît en haut puis regagne sa place
                self.y = -30
                self.etat = Ennemi.RETOUR
        elif self.etat == Ennemi.RETOUR:
            self.x += (fx - self.x) * 0.05
            self.y += (fy - self.y) * 0.05
            if abs(fx - self.x) < 2 and abs(fy - self.y) < 2:
                self.etat = Ennemi.FORMATION
        self.rect.center = (int(self.x), int(self.y))

    def points(self):
        base, pique = TYPES_ENNEMIS[self.type][2:]
        return pique if self.etat == Ennemi.PIQUE else base

    def draw(self, ecran, frame):
        corps, ailes = TYPES_ENNEMIS[self.type][:2]
        if self.type == "boss" and self.pv == 1:
            corps = ORANGE  # boss touché une fois
        x, y = int(self.x), int(self.y)
        battement = 4 if (frame // 15) % 2 else 0  # animation des ailes
        pygame.draw.polygon(ecran, ailes, [(x - 3, y - 2), (x - 13, y - 8 + battement), (x - 11, y + 6)])
        pygame.draw.polygon(ecran, ailes, [(x + 3, y - 2), (x + 13, y - 8 + battement), (x + 11, y + 6)])
        pygame.draw.ellipse(ecran, corps, (x - 6, y - 9, 12, 18))
        pygame.draw.circle(ecran, NOIR, (x - 2, y - 4), 2)
        pygame.draw.circle(ecran, NOIR, (x + 2, y - 4), 2)


# --------------------------------------------------------------------------
# Projectiles et explosions
# --------------------------------------------------------------------------
class Tir:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 1, y, 3, 10)

    def update(self):
        self.rect.y -= VITESSE_TIR

    def draw(self, ecran):
        pygame.draw.rect(ecran, JAUNE, self.rect)


class TirEnnemi:
    def __init__(self, x, y, cible_x):
        self.x, self.y = x, y
        self.vx = max(-2, min(2, (cible_x - x) / 120))
        self.rect = pygame.Rect(0, 0, 4, 8)

    def update(self):
        self.x += self.vx
        self.y += VITESSE_TIR_ENNEMI
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, ecran):
        pygame.draw.rect(ecran, ROUGE, self.rect)


class Explosion:
    def __init__(self, x, y, couleur):
        self.particules = []
        for _ in range(18):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(1, 4)
            self.particules.append([x, y, math.cos(a) * v, math.sin(a) * v])
        self.vie = 30
        self.couleur = couleur

    def update(self):
        self.vie -= 1
        for p in self.particules:
            p[0] += p[2]
            p[1] += p[3]

    def draw(self, ecran):
        for x, y, _, _ in self.particules:
            pygame.draw.circle(ecran, self.couleur, (int(x), int(y)), 2)


# --------------------------------------------------------------------------
# Jeu
# --------------------------------------------------------------------------
class Jeu:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Space Shooter")
        self.ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
        self.horloge = pygame.time.Clock()
        self.police = pygame.font.Font(None, 28)
        self.grande_police = pygame.font.Font(None, 56)
        self.etoiles = Etoiles()
        self.meilleur = 0
        self.etat = "titre"
        self.frame = 0
        self.pause = False

    # ----- gestion de partie -----
    def nouvelle_partie(self):
        self.score = 0
        self.vies = VIES_DEPART
        self.niveau = 0
        self.joueur = Joueur()
        self.niveau_suivant()
        self.etat = "jeu"

    def niveau_suivant(self):
        self.niveau += 1
        self.tirs = []
        self.tirs_ennemis = []
        self.explosions = []
        self.ennemis = []
        disposition = [
            ["", "", "", "boss", "boss", "boss", "boss", "", "", ""],
            ["", "papillon"] + ["papillon"] * 6 + ["papillon", ""],
            ["", "papillon"] + ["papillon"] * 6 + ["papillon", ""],
            ["abeille"] * 10,
            ["abeille"] * 10,
        ]
        for ligne, rangee in enumerate(disposition):
            for col, type_ in enumerate(rangee):
                if type_:
                    e = Ennemi(type_, col, ligne, self.niveau)
                    e.y -= col * 15 + ligne * 40  # arrivée échelonnée
                    self.ennemis.append(e)
        self.delai_pique = 120
        self.message_niveau = 90

    def perdre_vie(self):
        self.explosions.append(Explosion(*self.joueur.rect.center, BLANC))
        self.vies -= 1
        self.tirs_ennemis.clear()
        if self.vies <= 0:
            self.meilleur = max(self.meilleur, self.score)
            self.etat = "fin"
        else:
            self.joueur.reset()

    # ----- boucle principale -----
    def run(self):
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    pygame.quit()
                    return
                if ev.type == pygame.KEYDOWN:
                    self.touche(ev.key)
            if not self.pause:
                self.update()
            self.draw()
            self.horloge.tick(FPS)

    def touche(self, key):
        if self.etat in ("titre", "fin") and key == pygame.K_RETURN:
            self.nouvelle_partie()
        elif self.etat == "jeu":
            if key == pygame.K_p:
                self.pause = not self.pause
            elif key == pygame.K_SPACE and not self.pause and len(self.tirs) < MAX_TIRS_JOUEUR:
                self.tirs.append(Tir(self.joueur.rect.centerx, self.joueur.rect.top))

    def update(self):
        self.frame += 1
        self.etoiles.update()
        if self.etat != "jeu":
            return

        self.joueur.update(pygame.key.get_pressed())
        balancement = math.sin(self.frame / 50) * 20

        for e in self.ennemis:
            e.update(balancement, self.joueur, self.tirs_ennemis, self.niveau)

        # Déclenche un piqué de temps en temps
        if self.message_niveau > 0:
            self.message_niveau -= 1
        else:
            self.delai_pique -= 1
            if self.delai_pique <= 0:
                candidats = [e for e in self.ennemis if e.etat == Ennemi.FORMATION]
                nb = min(len(candidats), 1 + self.niveau // 3)
                for e in random.sample(candidats, nb):
                    e.lancer_pique(self.joueur.rect.centerx)
                self.delai_pique = max(40, random.randint(90, 160) - self.niveau * 10)

        for liste in (self.tirs, self.tirs_ennemis, self.explosions):
            for obj in liste:
                obj.update()
        self.tirs = [t for t in self.tirs if t.rect.bottom > 0]
        self.tirs_ennemis = [t for t in self.tirs_ennemis if t.rect.top < HAUTEUR]
        self.explosions = [x for x in self.explosions if x.vie > 0]

        # Collisions tirs du joueur / ennemis
        for t in self.tirs[:]:
            for e in self.ennemis:
                if t.rect.colliderect(e.rect):
                    self.tirs.remove(t)
                    e.pv -= 1
                    if e.pv <= 0:
                        self.score += e.points()
                        self.explosions.append(Explosion(e.x, e.y, TYPES_ENNEMIS[e.type][0]))
                        self.ennemis.remove(e)
                    break

        # Collisions avec le joueur
        if not self.joueur.invincible:
            zone = self.joueur.rect.inflate(-8, -6)
            touche = any(t.rect.colliderect(zone) for t in self.tirs_ennemis)
            for e in self.ennemis:
                if e.rect.colliderect(zone):
                    touche = True
                    self.explosions.append(Explosion(e.x, e.y, TYPES_ENNEMIS[e.type][0]))
                    self.ennemis.remove(e)
                    break
            if touche:
                self.perdre_vie()

        if not self.ennemis and self.etat == "jeu":
            self.niveau_suivant()

    # ----- affichage -----
    def texte(self, txt, police, couleur, centre):
        surf = police.render(txt, True, couleur)
        self.ecran.blit(surf, surf.get_rect(center=centre))

    def draw(self):
        self.ecran.fill(NOIR)
        self.etoiles.draw(self.ecran)

        if self.etat == "titre":
            self.texte("SPACE SHOOTER", self.grande_police, CYAN, (LARGEUR // 2, HAUTEUR // 3))
            if (self.frame // 30) % 2:
                self.texte("Appuyez sur ENTRÉE", self.police, BLANC, (LARGEUR // 2, HAUTEUR // 2))
            self.texte("← → : bouger    ESPACE : tirer    P : pause", self.police, JAUNE,
                       (LARGEUR // 2, HAUTEUR // 2 + 60))
            for i, (t, (c, _, p, pq)) in enumerate(TYPES_ENNEMIS.items()):
                self.texte(f"{p} / {pq} pts", self.police, c, (LARGEUR // 2, HAUTEUR // 2 + 120 + i * 30))
        else:
            for e in self.ennemis:
                e.draw(self.ecran, self.frame)
            for obj in self.tirs + self.tirs_ennemis + self.explosions:
                obj.draw(self.ecran)
            if self.etat == "jeu":
                self.joueur.draw(self.ecran)

            # HUD
            self.ecran.blit(self.police.render(f"SCORE {self.score}", True, BLANC), (10, 8))
            self.ecran.blit(self.police.render(f"RECORD {max(self.meilleur, self.score)}", True, ROUGE),
                            (LARGEUR - 160, 8))
            for i in range(self.vies - 1):
                dessiner_vaisseau(self.ecran, 20 + i * 26, HAUTEUR - 12, 0.6)
            self.texte(f"NIVEAU {self.niveau}", self.police, CYAN, (LARGEUR - 60, HAUTEUR - 12))

            if self.etat == "jeu" and self.message_niveau > 0:
                self.texte(f"NIVEAU {self.niveau}", self.grande_police, JAUNE, (LARGEUR // 2, HAUTEUR // 2))
            if self.pause:
                self.texte("PAUSE", self.grande_police, BLANC, (LARGEUR // 2, HAUTEUR // 2))
            if self.etat == "fin":
                self.texte("GAME OVER", self.grande_police, ROUGE, (LARGEUR // 2, HAUTEUR // 2))
                self.texte("ENTRÉE pour rejouer", self.police, BLANC, (LARGEUR // 2, HAUTEUR // 2 + 50))

        pygame.display.flip()


if __name__ == "__main__":
    Jeu().run()
