import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("codea-plus-2022")
print(h.finish(method="Not harvested. Home page read (corpuscodea.es, no robots.txt); no bulk export/API/OAI found, documents are viewable only one by one through the web interface (corpus/documento.php).",
 coverage="Nothing harvested (0 of 1,498 in-window documents).",
 problems=["The site's own 'Condiciones de uso' (CC BY-NC-ND) state: 'No está permitida la elaboración de obras derivadas (nuevos corpus, compilaciones, recopilaciones, proyectos) que reproduzcan en formato digital o en papel documentos del corpus CODEA+ 2022. Los materiales de CODEA podrán ser citados, pero no reutilizados.' Copying the documents into a staging corpus would be exactly that, so no text was downloaded. Needs the owners' (GITHE, Univ. de Alcalá) permission; to be decided by the project."]))
