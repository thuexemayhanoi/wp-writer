"""Protect public WordPress permalinks from spreadsheet-source metadata.

Only article subject matter (an approved title) may determine a NEW slug.
Never rewrite an existing permalink/canonical or "repair" a slug at publish time.
"""
import re
from common import norm, slugify

# These tokens describe the planning file, not a topic in the rental SEO plan.
SOURCE_FILE_TOKENS = frozenset({'excel', 'xlsx', 'xls', 'csv', 'spreadsheet'})
_BAD_PLAN_ID = re.compile(r'^TP-[0-9]{4}$')
_SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def suggested_slug(title, max_length=96):
    """Give authors an article-title-derived URL suggestion, never a file name."""
    parts = slugify(title).split('-')
    chosen = []
    for token in parts:
        if not token:
            continue
        tentative = '-'.join(chosen + [token])
        if len(tentative) > max_length and chosen:
            break
        chosen.append(token)
    return '-'.join(chosen)


def proposed_slug_errors(topic):
    """Fail closed on spreadsheet artifacts for TP-linked new articles.

    Legacy topics not linked to the spreadsheet remain unchanged, except for
    metadata leakage when a spreadsheet word is absent from the real title.
    """
    slug = str(topic.get('proposed_slug') or '')
    plan_id = topic.get('title_plan_id')
    errors = []
    if plan_id and not _BAD_PLAN_ID.fullmatch(str(plan_id)):
        errors.append('TITLE_PLAN_ID_INVALID')
    if not slug:
        return errors  # Existing manifest-required-field gate handles missing.
    tokens = set(slug.lower().split('-'))
    title_tokens = set(norm(topic.get('title', '')).split())
    if tokens & SOURCE_FILE_TOKENS and (
            plan_id or not (tokens & SOURCE_FILE_TOKENS) <= title_tokens):
        errors.append('SLUG_SOURCE_FILE_LEAK: remove excel/xlsx/csv from proposed_slug before QA')
    if plan_id:
        if not _SLUG_PATTERN.fullmatch(slug):
            errors.append('TITLE_PLAN_SLUG_FORMAT: use lowercase Vietnamese ASCII transliteration and hyphens')
        if len(slug) > 105:
            errors.append('TITLE_PLAN_SLUG_TOO_LONG: optimize before publishing')
        if re.search(r'(?:^|-)tp-[0-9]{4}(?:-|$)', slug):
            errors.append('SLUG_PLAN_ID_LEAK: keep TP-XXXX in tracking metadata only')
        if any(v in slug for v in (
                'seo-tieu-de-', 'file-excel', 'google-sheets',
                'tu-bang-tinh', 'tu-file-')):
            errors.append('SLUG_SOURCE_FILENAME_LEAK')
    return errors
