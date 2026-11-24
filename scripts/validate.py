#!/usr/bin/env python3
"""Validate source relationships and portable HTML without external packages.

Run from any directory: python scripts/validate.py
This command only reads project files and prints a JSON report. Exit code is 0
when all checks pass, 1 for validation failures, and 2 for input errors.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


HTML_FILES = ('index.html', 'slides.html', 'wiki.html', 'evidence.html')
EXPECTED_COUNTS = {'sources': 6, 'wiki_pages': 10, 'slides': 15, 'scenarios': 2}


class Report:
    def __init__(self):
        self.check_count = 0
        self.errors = []

    def check(self, condition, message):
        self.check_count += 1
        if not condition:
            self.errors.append(message)
        return bool(condition)


class HtmlInventory(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.langs = []
        self.charsets = []
        self.script_sources = []
        self.stylesheets = []
        self.style_text = []
        self.in_style = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a' and 'name' in attrs:
            self.ids.append(attrs['name'])
        if 'href' in attrs:
            self.links.append(attrs['href'] or '')
        if tag == 'html':
            self.langs.append(attrs.get('lang', ''))
        if tag == 'meta' and 'charset' in attrs:
            self.charsets.append((attrs['charset'] or '').lower())
        if tag == 'script' and 'src' in attrs:
            self.script_sources.append(attrs['src'])
        if tag == 'link' and 'stylesheet' in (attrs.get('rel') or '').lower().split():
            self.stylesheets.append(attrs.get('href', ''))
        if tag == 'style':
            self.in_style = True

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.style_text.append(data)


def load_records(root, relative):
    value = json.loads((root / relative).read_text(encoding='utf-8-sig'))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f'{relative}: expected an array of objects')
    return value


def record_index(records, label, report):
    ids = [r.get('id') for r in records]
    valid = all(isinstance(item, str) and item for item in ids)
    report.check(valid, f'{label}: each record needs a non-empty string ID')
    if not valid:
        return {}
    report.check(len(ids) == len(set(ids)), f'{label}: duplicate IDs')
    return {r['id']: r for r in records}


def reference_ids(record, field, label, report, require=True):
    value = record.get(field)
    valid = isinstance(value, list) and all(isinstance(item, str) and item for item in value)
    report.check(valid, f'{label}: {field} must be an array of IDs')
    if not valid:
        return set()
    if require:
        report.check(bool(value), f'{label}: {field} must not be empty')
    report.check(len(value) == len(set(value)), f'{label}: repeated IDs in {field}')
    return set(value)


def validate_records(root, report):
    sources = load_records(root, 'sources/manifest.json')
    cards = load_records(root, 'sources/evidence-cards.json')
    pages = load_records(root, 'wiki/pages.json')
    slides = load_records(root, 'slides/slides.json')
    source_map = record_index(sources, 'sources', report)
    card_map = record_index(cards, 'reference cards', report)
    wiki_map = record_index(pages, 'Wiki', report)
    record_index(slides, 'slides', report)
    report.check(len(sources) == EXPECTED_COUNTS['sources'], 'Expected 6 source records')
    report.check(len(pages) == EXPECTED_COUNTS['wiki_pages'], 'Expected 10 Wiki records')
    report.check(len(slides) == EXPECTED_COUNTS['slides'], 'Expected 15 slide records')
    report.check(set(card_map) == set(source_map), 'Reference cards and source IDs do not match')
    for sid, source in source_map.items():
        report.check(bool(source.get('title')), f'{sid}: source title is empty')
        url = urlsplit(str(source.get('url', '')))
        report.check(url.scheme in ('https', 'http') and bool(url.netloc), f'{sid}: source URL is not HTTP(S)')

    wiki_sources = {}
    for wid, page in wiki_map.items():
        declared = reference_ids(page, 'source_ids', wid, report)
        wiki_sources[wid] = declared
        report.check(declared <= source_map.keys(), f'{wid}: unknown source IDs {sorted(declared - source_map.keys())}')
        related = reference_ids(page, 'related', wid, report, require=False)
        report.check(related <= wiki_map.keys(), f'{wid}: unknown related Wiki IDs {sorted(related - wiki_map.keys())}')
        body = page.get('body')
        if report.check(isinstance(body, list) and bool(body), f'{wid}: body must be a non-empty array'):
            for i, section in enumerate(body):
                if not report.check(isinstance(section, dict), f'{wid} section {i+1}: expected an object'):
                    continue
                section_ids = reference_ids(section, 'source_ids', f'{wid} section {i+1}', report)
                report.check(section_ids <= declared, f'{wid} section {i+1}: sources are missing from the page declaration')

    scenarios = []
    for slide in slides:
        label = str(slide.get('id', '<missing slide ID>'))
        wiki_ids = reference_ids(slide, 'wiki_ids', label, report)
        source_ids = reference_ids(slide, 'source_ids', label, report)
        report.check(wiki_ids <= wiki_map.keys(), f'{label}: unknown Wiki IDs {sorted(wiki_ids - wiki_map.keys())}')
        report.check(source_ids <= source_map.keys(), f'{label}: unknown source IDs {sorted(source_ids - source_map.keys())}')
        supporting_sources = set().union(*(wiki_sources.get(wid, set()) for wid in wiki_ids))
        report.check(source_ids <= supporting_sources, f'{label}: slide sources are not supported by its referenced Wiki pages')
        for wid in wiki_ids & wiki_map.keys():
            report.check(bool(source_ids & wiki_sources.get(wid, set())), f'{label}: {wid} has no source in common with the slide')
        if slide.get('type') == 'scenario':
            scenarios.append(slide)
        elif 'scenario' in slide:
            report.check(False, f'{label}: scenario payload exists on a different slide type')
    report.check(len(scenarios) == EXPECTED_COUNTS['scenarios'], 'Expected 2 scenario slides')
    for slide in scenarios:
        label = slide.get('id', '<missing slide ID>')
        scenario = slide.get('scenario')
        if not report.check(isinstance(scenario, dict), f'{label}: scenario must be an object'):
            continue
        report.check(isinstance(scenario.get('question'), str) and bool(scenario['question'].strip()), f'{label}: scenario question is empty')
        options = scenario.get('options')
        valid_options = isinstance(options, list) and len(options) >= 2 and all(isinstance(option, str) and option.strip() for option in options)
        if report.check(valid_options, f'{label}: scenario options must contain at least two non-empty strings'):
            report.check(len(set(options)) == len(options), f'{label}: scenario options contain duplicates')
            answer = scenario.get('correct')
            report.check(type(answer) is int and 0 <= answer < len(options), f'{label}: correct must be a valid zero-based option index')
        explanation = scenario.get('explanation')
        report.check(isinstance(explanation, str) and bool(explanation.strip()), f'{label}: scenario explanation is empty')
    return {'sources': len(sources), 'wiki_pages': len(pages), 'slides': len(slides), 'scenarios': len(scenarios)}


def inspect_html(path):
    inventory = HtmlInventory()
    inventory.feed(path.read_text(encoding='utf-8'))
    inventory.close()
    return inventory


def validate_html(root, report):
    parsed = {}
    for name in HTML_FILES:
        path = root / name
        if not report.check(path.is_file(), f'{name}: file is missing'):
            continue
        try:
            page = inspect_html(path)
        except (UnicodeError, OSError) as error:
            report.check(False, f'{name}: cannot read UTF-8 HTML: {error}')
            continue
        parsed[path.resolve()] = page
        report.check(page.langs == ['zh-Hant'], f'{name}: expected one html element with lang=zh-Hant')
        report.check(page.charsets == ['utf-8'], f'{name}: expected one UTF-8 charset declaration')
        duplicates = sorted(key for key, count in Counter(page.ids).items() if count > 1)
        report.check(not duplicates, f'{name}: duplicate fragment IDs {duplicates}')
        report.check(not page.script_sources, f'{name}: script src dependency found')
        report.check(not page.stylesheets, f'{name}: stylesheet file dependency found')
        css = '\n'.join(page.style_text)
        report.check(not re.search(r'@import\b', css, re.IGNORECASE), f'{name}: CSS import dependency found')
        report.check(not re.search(r'url\(\s*[\"\x27]?(?:https?:)?//', css, re.IGNORECASE), f'{name}: remote CSS resource dependency found')

    local_links = 0
    fragment_links = 0
    for name in HTML_FILES:
        current = (root / name).resolve()
        if current not in parsed:
            continue
        for href in parsed[current].links:
            parts = urlsplit(href)
            if parts.scheme in ('https', 'http', 'mailto', 'tel') or parts.netloc:
                continue
            if not report.check(not parts.scheme, f'{name}: non-portable link scheme in {href!r}'):
                continue
            local_links += 1
            target = (current.parent / unquote(parts.path)).resolve() if parts.path else current
            try:
                target.relative_to(root)
            except ValueError:
                report.check(False, f'{name}: local link leaves the project directory: {href!r}')
                continue
            if not report.check(target.is_file(), f'{name}: missing local target {href!r}'):
                continue
            if parts.fragment:
                fragment_links += 1
                if target not in parsed and target.suffix.lower() in ('.html', '.htm'):
                    parsed[target] = inspect_html(target)
                if not report.check(target in parsed, f'{name}: fragment target is not an HTML document: {href!r}'):
                    continue
                fragment = unquote(parts.fragment)
                report.check(fragment in parsed[target].ids, f'{name}: missing anchor in {href!r}')
    return {'html_files': len([name for name in HTML_FILES if (root / name).resolve() in parsed]), 'local_links': local_links, 'fragment_links': fragment_links}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    report = Report()
    try:
        counts = validate_records(root, report)
        counts.update(validate_html(root, report))
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({'status': 'input_error', 'error': str(error)}, ensure_ascii=False, indent=2))
        return 2
    result = {'status': 'pass' if not report.errors else 'fail', 'checks': report.check_count, 'counts': counts, 'errors': report.errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not report.errors else 1


if __name__ == '__main__':
    sys.exit(main())
