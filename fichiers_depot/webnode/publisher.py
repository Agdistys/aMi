"""Public origin selected at build time. Leave GitHub Pages active until cutover."""
import os

GITHUB = 'https://agdistys.github.io/aMi/'
CUSTOM = 'https://ami.agdistys.fr/'
PUBLISHER = os.environ.get('AMI_PAGES_BASE') or GITHUB
if PUBLISHER not in (GITHUB, CUSTOM):
    raise ValueError('Adresse de publication aMi inconnue.')


def publisher_links(text):
    return text.replace(GITHUB, PUBLISHER)


def adapter_links(text):
    # Apply to generated code before computing its integrity. The published
    # volume bytes are still the original material checked by that code.
    if PUBLISHER == GITHUB:
        return text
    return (publisher_links(text)
            .replace("'https://agdistys.github.io'", "'https://ami.agdistys.fr'")
            .replace("'/aMi/volumes_protocole/'", "'/volumes_protocole/'")
            .replace(r'\/aMi\/annexes\/', r'\/annexes\/'))
