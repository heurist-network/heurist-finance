"""Evidence-backed event dates, separate from publication and ingestion time.

Pure rendering never mutates stored publisher timestamps. Only a reviewed exact
story/URL correction or validated source-anchored assessment can override time.
Unknown, conflicting and mixed-event records remain explicitly qualified.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

UNKNOWN = 'EVENT DATE UNVERIFIED: publication/ingestion time does not establish when the underlying event occurred. Verify the original source before calling it new.'
PRIMARY_HOSTS = {'sec.gov', 'fda.gov', 'clinicaltrials.gov', 'nvidianews.nvidia.com',
                 'investor.nvidia.com', 'news.modernatx.com', 'investors.modernatx.com',
                 'ir.crisprtx.com', 'recursion.com', 'investors.duolingo.com',
                 'duolingo.gcs-web.com', 'investors.airbnb.com', 'pr.tsmc.com'}


def day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def canonical_url(value):
    p = urlsplit(str(value or ''))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), '', ''))


def load_corrections():
    path = Path(__file__).with_name('event_corrections.json')
    return json.loads(path.read_text()) if path.exists() else []


def age_words(days):
    if days >= 60:
        return f'about {days // 30} months ago ({days} days)'
    if days >= 14:
        return f'about {days // 7} weeks ago ({days} days)'
    return f'{days} days ago'


def validate_assessment(assessment, documents, *, now=None):
    """Validate model output against an explicit dated excerpt in a primary body.

    Date extraction alone never creates an assessment. The synthesizer must
    classify the excerpt as the SAME occurred event, with no new development
    for whole-event correction; conflicts/uncertainty must stay unverified.
    """
    now = day(now) or datetime.now(timezone.utc).date()
    a = dict(assessment or {})
    d = day(a.get('event_date'))
    if (a.get('confidence') != 'high' or a.get('status') not in {'recycled', 'mixed'}
            or not d or d > now or not a.get('reason')):
        return None
    if a['status'] == 'recycled' and a.get('new_development') is not False:
        return None
    source = next((x for x in documents if x.get('id') == a.get('source_doc_id')), None)
    if not source:
        return None
    host = (urlsplit(source.get('url', '')).hostname or '').removeprefix('www.')
    if host not in PRIMARY_HOSTS:
        return None
    quote = ' '.join(str(a.get('evidence_quote', '')).split())
    body = ' '.join(str(source.get('body', '')).split())
    if len(quote) < 40 or quote not in body:
        return None
    # Require the exact date in the quoted evidence; no guessing years from URLs.
    forms = [d.isoformat(), f'{d.strftime("%B")} {d.day}, {d.year}',
             f'{d.day} {d.strftime("%B")} {d.year}']
    if not any(x.lower() in quote.lower() for x in forms):
        return None
    a.update(evidence_url=source['url'], verified_at=now.isoformat(),
             method='primary_excerpt', scope='whole_event' if a['status'] == 'recycled' else 'component')
    return a


def timing(item, *, now=None, corrections=None):
    now = day(now) or datetime.now(timezone.utc).date()
    corrections = load_corrections() if corrections is None else corrections
    identifier = item.get('id') or item.get('story_id') or item.get('doc_id')
    urls = {canonical_url(item.get('url'))} | {canonical_url(x.get('url')) for x in item.get('sources', []) if isinstance(x, dict)}
    candidates = [x for x in corrections if
                  (identifier and identifier in x.get('story_ids', [])) or
                  any(canonical_url(u) in urls for u in x.get('article_urls', []))]
    supplied = item.get('event_assessment')
    if isinstance(supplied, dict) and supplied.get('method') == 'primary_excerpt':
        candidates.append(supplied)
    valid = [x for x in candidates if x.get('confidence') == 'high'
             and x.get('scope') in {'whole_event', 'component'} and day(x.get('event_date'))
             and day(x['event_date']) <= now and day(x.get('verified_at'))
             and day(x['verified_at']) <= now and x.get('evidence_url') and x.get('reason')]
    original = (supplied or {}).get('original_published_at') or item.get('original_created_at') or item.get('original_published_at') or item.get('created_at') or item.get('published_at')
    base = {'event_date': None, 'effective_at': original, 'original_timestamp': original,
            'status': 'unverified', 'context': UNKNOWN, 'evidence': []}
    if not valid:
        return base
    if (day(original) and any(day(x['event_date']) > day(original) for x in valid)) or len({x['event_date'] for x in valid}) != 1:
        return {**base, 'status': 'conflicting', 'context': 'CONFLICTING EVENT DATES: retain article timestamp; resolve primary evidence before interpreting recency.'}
    event = valid[0]['event_date']
    # A component notice can never cause an entire mixed story to be backdated.
    whole = all(x['scope'] == 'whole_event' for x in valid)
    lag = (now - day(event)).days
    label = 'OLD EVENT' if lag >= 7 else 'EVENT DATE VERIFIED'
    note = f'{label}: {event}, {age_words(lag)} as of {now.isoformat()}. '
    if whole:
        note += 'The underlying event is dated to its original announcement; a recent article or ingestion timestamp is not a new catalyst. '
    else:
        note += 'This date applies only to the identified background component; newer developments in this story retain their own dates. '
    note += ' '.join(dict.fromkeys(x['reason'] for x in valid))
    note += ' Evidence: ' + ', '.join(dict.fromkeys(x['evidence_url'] for x in valid))
    return {'event_date': event, 'effective_at': event + 'T00:00:00Z' if whole else original,
            'original_timestamp': original, 'status': 'verified_old_event' if whole else 'mixed',
            'date_precision': 'day', 'age_days': lag, 'context': note, 'evidence': valid}


def annotate(item, *, now=None, corrections=None):
    out = deepcopy(item)
    t = timing(out, now=now, corrections=corrections)
    out['temporal_context'] = t
    out['event_date'] = t['event_date']
    out['effective_at'] = t['effective_at']
    if t['status'] == 'verified_old_event':
        for field in ('created_at', 'published_at'):
            if out.get(field):
                out.setdefault('original_' + field, out[field])
                out[field] = t['effective_at']
    return out


def annotate_payload(payload, *, now=None):
    out = deepcopy(payload)
    if isinstance(out, dict) and (isinstance(out.get('stories'), list) or isinstance(out.get('items'), list)):
        key = 'stories' if 'stories' in out else 'items'
        out[key] = [x if isinstance(x.get('temporal_context'), dict) else annotate(x, now=now) for x in out[key]]
        out['timestamp_policy'] = 'Use effective_at and temporal_context for event recency. Original article dates are preserved; unverified does not mean fresh.'
    elif isinstance(out, dict):
        # A pre-generated brief is not itself evidence of a fresh event.
        for theme in out.get('themes', []):
            if not isinstance(theme, dict):
                continue
            components = []
            for sid in theme.get('source_story_ids', []):
                event = timing({'id': sid}, now=now)
                if event['status'] in {'verified_old_event', 'mixed'}:
                    components.append({'story_id': sid, **event})
            if components:
                theme['source_event_context'] = components
        out['timestamp_policy'] = 'This is a generated summary. Its date is not an event date; verify underlying stories and primary releases before using a claim as new evidence.'
    return out
