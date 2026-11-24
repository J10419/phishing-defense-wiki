#!/usr/bin/env python3
"""Render the approved Wiki and slide records as dependency-free, offline HTML.

Run from any directory: python scripts/render_site.py
Use --root PATH to render a separate fixture or copy. This renderer adds no facts.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def lines(value):
    return esc(value).replace("\n", "<br>")


def ident(value):
    return re.sub(r"[^A-Za-z0-9_-]", "-", str(value))


STYLE = r"""
:root{--navy:#142b3a;--navy2:#203e4f;--paper:#f7f5ef;--white:#fffefb;--ink:#152c39;--muted:#53636c;--line:#d7ddd9;--orange:#c64926;--pale:#f7e7dd;--green:#276151;--mint:#e2eee7;--shadow:0 20px 80px #132b3b12;font-family:'Noto Sans TC','Microsoft JhengHei','PingFang TC',system-ui,sans-serif;color:var(--ink);background:var(--paper);font-synthesis:none}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;line-height:1.75}button,input,select{font:inherit}button,a,input,summary{touch-action:manipulation}a{color:inherit;text-underline-offset:.25em;text-decoration-thickness:1px}a:hover{color:var(--orange)}button{cursor:pointer}button:disabled{opacity:.35;cursor:not-allowed}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--orange);outline-offset:5px}::selection{background:#f2c9b8;color:var(--ink)}[hidden]{display:none!important}.skip{position:fixed;top:-8em;left:1em;background:var(--white);padding:.6em;z-index:99}.skip:focus{top:1em}.topbar{min-height:76px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:20px;padding:15px max(28px,calc((100vw - 1320px)/2));background:var(--paper);position:relative;z-index:3}.brand{text-decoration:none;font-weight:800;letter-spacing:.08em;display:flex;gap:12px;align-items:center;white-space:nowrap}.brand-symbol{font-family:Georgia,serif;color:var(--orange);font-size:32px;line-height:1}.brand small{font-size:11px;display:block;letter-spacing:.12em;font-weight:500;color:var(--muted);line-height:1.2}.nav{display:flex;gap:25px;align-items:center;font-size:14px}.nav a{text-decoration:none}.nav a[aria-current=page]{color:var(--orange);font-weight:800}.wrap{width:min(1180px,calc(100% - 64px));margin:auto}.eyebrow{color:var(--orange);font-size:12px;font-weight:800;letter-spacing:.17em;text-transform:uppercase;margin:0 0 20px}.muted{color:var(--muted)}h1,h2,h3,p{margin-top:0}h1,h2,h3{line-height:1.35;letter-spacing:-.035em}h1{font-size:clamp(38px,5.6vw,72px)}h2{font-size:clamp(28px,3vw,42px)}h3{font-size:22px}p:last-child{margin-bottom:0}.button{display:inline-flex;justify-content:center;align-items:center;gap:14px;border:1px solid var(--navy);background:var(--navy);color:white;text-decoration:none;padding:13px 22px;font-size:15px;font-weight:700;border-radius:3px;min-height:48px}.button:hover{background:var(--navy2);color:white}.button.secondary{background:transparent;color:var(--ink);border-color:var(--line)}.button.secondary:hover{border-color:var(--navy)}.button.accent{background:var(--orange);border-color:var(--orange);color:white}.text-link{font-size:14px}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.page-footer{padding:32px 0 40px;border-top:1px solid var(--line);font-size:13px;color:var(--muted);margin-top:60px;display:flex;justify-content:space-between;gap:20px}.hero{display:grid;grid-template-columns:1.3fr .7fr;gap:80px;align-items:center;padding:82px 0 72px}.hero h1{margin-bottom:26px}.hero .lead{font-size:20px;max-width:38em;color:var(--muted)}.hero-art{background:var(--navy);color:var(--paper);padding:46px 38px;position:relative;min-height:340px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden}.hero-art .huge{font:210px/.85 Georgia,serif;color:#c2d5d033;position:absolute;right:-15px;top:55px;transform:rotate(-15deg);user-select:none}.hero-art .art-top{font-size:11px;letter-spacing:.16em;position:relative}.hero-art .art-bottom{font-size:28px;line-height:1.45;font-weight:700;position:relative}.hero-art .art-bottom span{color:#f2b69e}.stats{display:flex;gap:0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.stat{flex:1;padding:27px 30px 27px 0}.stat+.stat{padding-left:40px;border-left:1px solid var(--line)}.stat strong{font-size:36px;line-height:1.2;display:block;font-weight:500}.stat span{font-size:13px;color:var(--muted)}.section{padding:64px 0 0}.section-header{display:flex;align-items:baseline;justify-content:space-between;gap:20px;margin-bottom:30px}.section-header h2{margin-bottom:0}.destination{display:grid;grid-template-columns:54px 1fr 28px;gap:18px;padding:28px 0;border-bottom:1px solid var(--line);text-decoration:none}.destination .number{font-size:13px;color:var(--orange);padding-top:8px}.destination h3{margin:0 0 8px}.destination p{margin:0;color:var(--muted);font-size:15px}.destination .arrow{font-size:26px;align-self:center}.notice{margin:30px 0 0;padding:20px 24px;border-left:3px solid var(--orange);background:var(--pale);font-size:14px}.page-intro{padding:60px 0 34px;max-width:880px}.page-intro h1{font-size:clamp(34px,4.5vw,52px);margin-bottom:20px}.page-intro p{font-size:18px;color:var(--muted)}
/* Slide stage: content can scroll on short screens rather than being clipped. */
.deck-body{background:var(--paper)}.deck-body .topbar{min-height:66px;padding-top:10px;padding-bottom:10px}.deck-body .brand small{display:none}.deck-main{width:min(1240px,calc(100% - 80px));margin:auto}.slide{display:none;min-height:calc(100dvh - 162px);padding:50px 0 34px;flex-direction:column;position:relative}.slide.active{display:flex}.slide-top{display:flex;justify-content:space-between;gap:20px;margin-bottom:21px}.slide-top .eyebrow{margin:0}.slide-id{font-size:12px;color:var(--muted);letter-spacing:.15em}.slide h1{font-size:clamp(35px,4.4vw,62px);max-width:19em;margin-bottom:24px}.slide .slide-lead{font-size:clamp(19px,2.1vw,28px);line-height:1.7;max-width:39em;margin-bottom:24px;color:var(--muted)}.slide-copy{flex:1}.slide-bullets{padding:0;list-style:none;margin:18px 0 28px;max-width:54em}.slide-bullets li{font-size:clamp(17px,1.7vw,23px);padding:13px 0 13px 34px;border-bottom:1px solid var(--line);position:relative}.slide-bullets li:before{content:'—';position:absolute;left:0;color:var(--orange);font-weight:700}.slide-bullets li:last-child{border:0}.slide-foot{display:flex;flex-wrap:wrap;align-items:center;gap:16px;padding-top:16px;border-top:1px solid var(--line);margin-top:22px;font-size:12px;color:var(--muted)}.slide-foot details{margin-left:auto;max-width:100%;text-align:left}.slide-foot details[open]{flex-basis:100%;margin-left:0}.slide-foot summary{cursor:pointer;font-weight:700;color:var(--ink)}.sources-list{margin:12px 0 0;padding-left:20px;line-height:1.7;overflow-wrap:anywhere}.sources-list li{margin:6px 0}.source-id{font-family:ui-monospace,monospace;color:var(--orange);font-size:12px}.slide-note{border-left:3px solid var(--orange);background:var(--pale);padding:12px 18px;font-size:15px;max-width:68em;margin:20px 0 0}.cover .slide-copy{display:grid;grid-template-columns:1.4fr .6fr;gap:50px;align-items:center}.cover h1{font-size:clamp(42px,5.4vw,76px);max-width:13em}.cover .cover-mark{color:#bacac6;font:clamp(150px,25vw,340px)/1 Georgia,serif;user-select:none;text-align:center;transform:rotate(-12deg)}.cover .slide-lead{font-size:24px}.cover .slide-bullets li{font-size:17px}.deck-controls{position:sticky;bottom:0;background:var(--navy);color:var(--paper);z-index:4;min-height:84px;padding:13px 30px;display:flex;align-items:center;justify-content:space-between;gap:20px}.control-center{display:flex;align-items:center;gap:18px}.deck-controls button{border:1px solid #8a9da8;background:transparent;color:var(--paper);border-radius:3px;padding:8px 18px;min-height:44px;font-size:14px}.deck-controls button:hover:not(:disabled){background:#365465}.deck-controls #next{background:var(--paper);color:var(--navy);border-color:var(--paper)}.deck-controls #counter{min-width:72px;text-align:center;font-size:15px;font-variant-numeric:tabular-nums}.deck-controls .shortcut{font-size:12px;color:#bdcbd1}.progress{position:absolute;left:0;top:0;height:3px;background:#e78f6c;transition:width .2s}.example-layout{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:start}.mail{background:var(--white);border:1px solid var(--line);box-shadow:var(--shadow);overflow:hidden}.mail-title{background:#e9eeeb;border-bottom:1px solid var(--line);padding:12px 22px;font-size:12px;letter-spacing:.12em}.mail-head{padding:24px 25px 15px;font-size:14px}.mail-head p{margin:0 0 8px;overflow-wrap:anywhere}.mail-head strong{display:inline-block;min-width:56px;color:var(--muted);font-weight:500}.mail-body{padding:10px 25px 28px;font-size:19px;line-height:1.9;overflow-wrap:anywhere;white-space:normal}.example-caption{font-size:12px;color:var(--muted);margin-top:10px}.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px;margin:24px 0 30px;list-style:none;padding:0;counter-reset:step}.flow li{counter-increment:step;border-top:3px solid var(--orange);padding:17px 15px 17px 0;position:relative;font-size:18px;line-height:1.6}.flow li:before{content:counter(step,decimal-leading-zero);display:block;font-size:12px;letter-spacing:.1em;color:var(--orange);margin-bottom:12px}.scenario{max-width:890px}.scenario h2{font-size:24px;margin-bottom:22px}.scenario-options{display:grid;gap:12px}.scenario-option{display:flex;gap:18px;align-items:center;text-align:left;background:var(--white);border:1px solid var(--line);border-radius:3px;padding:15px 20px;font-size:18px;color:var(--ink);min-height:62px}.scenario-option:hover{border-color:var(--navy)}.scenario-option .letter{font-size:13px;color:var(--orange);min-width:20px}.scenario-option.correct{border-color:var(--green);background:var(--mint)}.scenario-option.wrong{border-color:var(--orange);background:var(--pale)}.scenario-result{margin:18px 0 0;padding:18px 22px;background:var(--mint);border-left:3px solid var(--green);font-size:17px}.scenario-result.wrong{background:var(--pale);border-color:var(--orange)}dialog{width:min(680px,calc(100% - 36px));max-height:85dvh;border:0;padding:28px;background:var(--paper);color:var(--ink);box-shadow:0 30px 150px #0004}dialog::backdrop{background:#102936bb;backdrop-filter:blur(3px)}.dialog-head{display:flex;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid var(--line);padding-bottom:18px}.dialog-head h2{font-size:24px;margin:0}.dialog-head button{border:1px solid var(--line);background:transparent;padding:5px 12px;min-height:40px;color:var(--ink)}.toc-list{list-style:none;padding:0;margin:15px 0 0}.toc-list a{display:flex;gap:20px;padding:11px 2px;border-bottom:1px solid var(--line);text-decoration:none;font-size:16px}.toc-list span{color:var(--orange);font-size:12px;min-width:26px;padding-top:4px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
/* Wiki and evidence */
.wiki-toolbar{position:sticky;top:0;z-index:2;background:var(--paper);padding:20px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);display:flex;gap:22px;align-items:center}.search-field{flex:1;position:relative}.search-field label{font-size:12px;display:block;color:var(--muted);margin-bottom:6px}.search-field input{background:var(--white);color:var(--ink);border:1px solid #a5b4b9;border-radius:3px;padding:12px 16px;width:100%;font-size:16px;min-height:48px}.search-count{font-size:13px;color:var(--muted);min-width:85px;padding-top:24px}.wiki-layout{display:grid;grid-template-columns:230px 1fr;gap:55px;padding-top:40px}.wiki-index{align-self:start;position:sticky;top:145px;max-height:calc(100dvh - 170px);overflow:auto;font-size:14px;padding-right:16px}.wiki-index h2{font-size:12px;letter-spacing:.15em;font-weight:700;color:var(--muted)}.wiki-index a{display:block;border-left:2px solid var(--line);padding:9px 0 9px 15px;text-decoration:none}.wiki-index a:hover{border-color:var(--orange)}.wiki-index .source-id{margin-right:8px}.wiki-entry{background:var(--white);border:1px solid var(--line);padding:35px 38px;margin-bottom:30px;scroll-margin-top:150px}.wiki-entry:target{border-top:4px solid var(--orange)}.wiki-entry h2{font-size:29px;margin-bottom:14px}.wiki-entry .summary{font-size:18px;color:var(--muted);padding-bottom:22px;margin-bottom:26px;border-bottom:1px solid var(--line)}.wiki-entry h3{font-size:20px;margin:24px 0 10px}.wiki-entry .body-text{font-size:16px;line-height:1.9}.inline-refs{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;margin:9px 0 0;color:var(--orange)}.related{border-top:1px solid var(--line);margin:26px 0 0;padding-top:16px;font-size:13px}.related a{margin-right:14px}.source-section{padding:35px 0 0;scroll-margin-top:130px}.source-section h2{font-size:30px}.source-item{border-top:1px solid var(--line);padding:21px 0;scroll-margin-top:140px}.source-item h3{font-size:17px;margin-bottom:8px}.source-item p{font-size:13px;margin-bottom:6px;color:var(--muted);overflow-wrap:anywhere}.source-item a{overflow-wrap:anywhere}.empty-search{padding:40px 0;font-size:18px}.evidence-menu{display:flex;flex-wrap:wrap;gap:9px;margin:24px 0 35px}.evidence-menu a{font-size:13px;padding:7px 11px;border:1px solid var(--line);text-decoration:none}.document{background:var(--white);border:1px solid var(--line);padding:30px 34px;margin:25px 0;scroll-margin-top:25px}.document h2{font-size:25px}.document pre{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;font-size:15px;line-height:1.9;tab-size:2;margin:20px 0 0}.document .doc-file{font-size:12px;color:var(--muted)}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:13px 14px;border-bottom:1px solid var(--line)}th{background:#e9eeeb;font-weight:700}td:first-child{white-space:nowrap}td a{margin-right:8px}.evidence-links{display:flex;gap:15px;flex-wrap:wrap;font-size:14px;padding:20px 0}.no-js{background:var(--pale);color:var(--ink);padding:15px 25px}
.inline-refs .locator{font-size:12px;color:var(--muted);line-height:1.7;overflow-wrap:anywhere}.source-item .source-summary{font-size:15px;color:var(--ink);line-height:1.85;margin:14px 0}.workflow-figure{margin:0;padding:30px;border:1px solid var(--line);background:var(--white)}.workflow-prelude{font-size:13px;color:var(--muted);margin:0 0 24px}.workflow-graph{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:auto auto;gap:42px 28px}.workflow-node{position:relative;min-width:0;border-top:3px solid var(--orange);background:var(--paper);padding:17px 16px;min-height:112px}.workflow-node:after{content:'→';position:absolute;right:-23px;top:43px;font-size:21px;color:var(--orange);font-weight:500}.workflow-node:nth-child(5):after{content:'↓';right:calc(50% - 6px);top:auto;bottom:-36px}.workflow-node:nth-child(6){grid-column:5;grid-row:2}.workflow-node:nth-child(7){grid-column:4;grid-row:2}.workflow-node:nth-child(8){grid-column:3;grid-row:2}.workflow-node:nth-child(9){grid-column:2;grid-row:2}.workflow-node:nth-child(10){grid-column:1;grid-row:2;border-top-color:var(--green);background:var(--mint)}.workflow-node:nth-child(n+6):after{content:'←';right:auto;left:-23px}.workflow-node:last-child:after{display:none}.workflow-node .step-num{font-size:10px;color:var(--orange);letter-spacing:.1em;display:block;margin-bottom:8px}.workflow-node strong{display:block;font-size:17px;line-height:1.4;font-weight:700}.workflow-node small{display:block;margin-top:6px;font-size:11px;color:var(--muted);line-height:1.6}.workflow-loops{display:grid;gap:8px;margin-top:27px;border-top:1px dashed #aab9bf;padding-top:20px}.workflow-loops p{font-size:13px;margin:0;line-height:1.8;color:var(--muted)}.workflow-loops .loop-arrow{color:var(--orange);font-size:18px;margin-right:8px}.workflow-figure figcaption{font-size:12px;color:var(--muted);margin-top:23px}
@media(max-width:650px){.workflow-figure{padding:23px 22px}.workflow-graph{display:block}.workflow-node{min-height:0;padding:14px 17px;margin-bottom:34px;display:grid;grid-template-columns:32px 1fr;column-gap:9px;align-items:center}.workflow-node .step-num{grid-row:1/3;margin:0}.workflow-node strong{font-size:18px}.workflow-node small{grid-column:2;margin-top:3px;font-size:12px}.workflow-node:after,.workflow-node:nth-child(5):after,.workflow-node:nth-child(n+6):after{content:'↓';right:auto;left:calc(50% - 6px);top:auto;bottom:-31px;font-size:20px}.workflow-node:last-child{margin-bottom:0}.workflow-loops{margin-top:23px}.workflow-loops p{font-size:12px}}
@media print{.workflow-figure{break-inside:avoid;box-shadow:none}.workflow-node{min-height:90px}.workflow-figure figcaption{font-size:9pt}}
@media(min-width:1600px){.slide{padding-top:68px}.slide-bullets li{padding-top:18px;padding-bottom:18px}}
@media(max-width:900px){.hero{gap:35px;grid-template-columns:1.3fr .7fr;padding:55px 0}.hero-art{padding:30px 24px;min-height:310px}.hero-art .art-bottom{font-size:24px}.wiki-layout{grid-template-columns:180px 1fr;gap:25px}.wiki-entry{padding:28px 25px}.deck-main{width:calc(100% - 56px)}.example-layout{gap:25px}.slide{padding-top:35px}.cover .slide-copy{grid-template-columns:1fr .35fr;gap:20px}.cover .cover-mark{font-size:180px}.deck-controls .shortcut{display:none}.slide .slide-lead{font-size:22px}.slide-bullets li{font-size:20px}}
@media(max-width:650px){.wrap{width:calc(100% - 36px)}.topbar{padding:13px 18px;gap:15px;min-height:64px}.brand{font-size:13px;gap:8px;letter-spacing:.04em}.brand-symbol{font-size:27px}.brand small{font-size:9px}.nav{gap:13px;font-size:12px}.nav .optional{display:none}.hero{grid-template-columns:1fr;gap:30px;padding:42px 0}.hero h1{font-size:42px}.hero .lead{font-size:18px}.hero-art{min-height:190px;display:none}.stats .stat{padding:20px 9px}.stat+.stat{padding-left:15px}.stat strong{font-size:29px}.stat span{font-size:11px}.section{padding-top:42px}.section-header{display:block}.section-header .muted{margin-top:10px;font-size:13px}.destination{grid-template-columns:28px 1fr 20px;gap:12px}.destination h3{font-size:21px}.destination p{font-size:14px}.page-footer{flex-direction:column;gap:8px;font-size:12px;margin-top:40px}.page-intro{padding:40px 0 25px}.page-intro p{font-size:16px}.deck-body .topbar{min-height:60px}.deck-main{width:calc(100% - 36px)}.slide{min-height:calc(100dvh - 137px);padding:26px 0}.slide-top{margin-bottom:18px}.slide-top .eyebrow{font-size:10px;letter-spacing:.1em}.slide-id{font-size:10px}.slide h1{font-size:34px;margin-bottom:18px;line-height:1.38}.slide .slide-lead{font-size:19px;margin-bottom:18px}.slide-bullets{margin:12px 0 20px}.slide-bullets li{font-size:17px;padding:12px 0 12px 25px;line-height:1.8}.slide-note{font-size:13px;padding:12px 14px}.slide-foot{font-size:11px;gap:10px;padding-top:13px;margin-top:18px}.cover .slide-copy{display:block;padding-top:25px}.cover h1{font-size:42px}.cover .cover-mark{display:none}.cover .slide-lead{font-size:20px}.cover .slide-bullets li{font-size:16px}.deck-controls{min-height:77px;padding:12px 16px;gap:8px}.deck-controls button{padding:8px 12px;font-size:13px}.control-center{gap:8px}.deck-controls #counter{min-width:53px;font-size:13px}.deck-controls .print-button{display:none}.example-layout{grid-template-columns:1fr;gap:12px}.mail-head{padding:17px 19px 10px;font-size:13px}.mail-body{padding:8px 19px 22px;font-size:17px}.mail-title{padding:10px 19px}.flow{grid-template-columns:1fr 1fr;gap:10px 18px}.flow li{font-size:16px;padding:12px 0}.flow li:before{margin-bottom:7px}.scenario h2{font-size:20px}.scenario-option{font-size:16px;padding:13px 14px;gap:12px}.scenario-result{font-size:15px;padding:14px 16px}.wiki-toolbar{gap:12px;padding:14px 0}.search-count{font-size:12px;min-width:64px}.wiki-layout{display:block;padding-top:25px}.wiki-index{position:static;max-height:none;margin-bottom:28px;display:flex;flex-wrap:wrap;gap:8px;padding:0}.wiki-index h2{width:100%;margin-bottom:4px}.wiki-index a{border:1px solid var(--line);padding:6px 10px;font-size:12px}.wiki-entry{padding:26px 22px;scroll-margin-top:125px}.wiki-entry h2{font-size:25px}.wiki-entry .summary{font-size:16px}.wiki-entry h3{font-size:19px}.wiki-entry .body-text{font-size:15px}.document{padding:25px 20px}.document h2{font-size:23px}.document pre{font-size:14px}th,td{padding:10px;font-size:12px}}
@media(max-width:380px){.deck-controls{padding:10px;gap:6px}.deck-controls button{padding:8px}.control-center{gap:6px}.deck-controls #counter{min-width:45px}.topbar .brand{font-size:12px}.topbar .nav{gap:10px;font-size:11px}}
@media screen{.slide:not(.active){display:none}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.progress{transition:none}}
@media print{body{background:white;color:black}.topbar,.deck-controls,.skip,.wiki-toolbar,.wiki-index,.evidence-menu,.print-hide{display:none!important}.deck-main,.wrap{width:100%;max-width:none}.slide{display:flex!important;min-height:0;padding:15mm 8mm 8mm;break-after:page;page-break-after:always}.slide:last-child{break-after:auto}.slide h1,.cover h1{font-size:30pt}.slide .slide-lead{font-size:16pt}.slide-bullets li{font-size:14pt;padding:8px 0 8px 25px}.cover .slide-copy{display:block}.cover .cover-mark{display:none}.slide-foot{font-size:9pt}.slide-foot details{display:block}.slide-foot details>*{display:block}.slide-foot details .sources-list{display:block!important}.slide-foot summary{list-style:none}.slide-note{font-size:11pt}.slide-top .eyebrow{font-size:10pt}.mail{box-shadow:none}.scenario-options{gap:8px}.scenario-option{font-size:13pt}.scenario-result{font-size:12pt}.flow li{font-size:12pt}.wiki-layout{display:block}.wiki-entry,.document{border:0;padding:15px 0;break-inside:avoid}.wiki-entry[hidden]{display:block!important}.page-footer{display:none}.page-intro{padding:20px 0}.source-item{break-inside:avoid}a{color:inherit}.hero-art{display:none}.hero{display:block;padding:20px 0}details{display:block}.sources-list{display:block}@page{size:A4 landscape;margin:12mm}}
"""


def document(title, body, current="", extra_script="", body_class=""):
    nav_items = []
    for key, file, label in [
        ("slides", "slides.html", "簡報"), ("wiki", "wiki.html", "Wiki"),
        ("evidence", "evidence.html", "驗證")]:
        current_attr = ' aria-current="page"' if key == current else ''
        nav_items.append(f'<a href="{file}"{current_attr}>{label}</a>')
    nav = ''.join(nav_items)
    return f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="釣魚郵件辨識與帳號防護：結合來源引用、Wiki 條目與互動簡報的資安知識庫。"><title>{esc(title)}｜釣魚防護知識庫</title><style>{STYLE}</style></head>
<body class="{esc(body_class)}"><a class="skip" href="#main">跳到主要內容</a><header class="topbar"><a class="brand" href="index.html"><span class="brand-symbol" aria-hidden="true">@</span><span>釣魚防護知識庫<small>PHISHING · ACCOUNT SECURITY</small></span></a><nav class="nav" aria-label="主導覽">{nav}</nav></header>{body}{extra_script}</body></html>'''


def source_refs(ids, source_map):
    items = []
    for sid in dict.fromkeys(ids):
        item = source_map.get(sid, {})
        title = item.get("title", sid)
        url = item.get("url", "wiki.html#source-" + ident(sid))
        # Only external HTTP(S) URLs from the reviewed manifest are linked externally.
        if not str(url).startswith(("https://", "http://")):
            url = "wiki.html#source-" + ident(sid)
        items.append(f'<li><span class="source-id">{esc(sid)}</span> <a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(title)}</a></li>')
    return '<ul class="sources-list">' + "".join(items) + '</ul>' if items else '<p>此頁說明專案流程，詳見對應 Wiki 條目。</p>'


def slide_footer(slide, source_map):
    refs = " ".join(f'<a href="wiki.html#{ident(w)}">{esc(w)}</a>' for w in slide.get("wiki_ids", []))
    sources = " ".join(f'<a href="wiki.html#source-{ident(s)}">{esc(s)}</a>' for s in slide.get("source_ids", []))
    return f'<footer class="slide-foot"><span>知識依據　{refs or "專案紀錄"}</span><span>來源　{sources or "專案紀錄"}</span><details><summary>查看來源與出處</summary>{source_refs(slide.get("source_ids", []), source_map)}</details></footer>'


def render_slides(slides, source_map):
    sections, toc = [], []
    for i, slide in enumerate(slides):
        sid = ident(slide["id"])
        title, kind = esc(slide["title"]), slide.get("type", "normal")
        bullet_html = '<ul class="slide-bullets">' + ''.join(f'<li>{lines(b)}</li>' for b in slide.get("bullets", [])) + '</ul>' if slide.get("bullets") else ''
        lead = f'<p class="slide-lead">{lines(slide.get("lead", ""))}</p>' if slide.get("lead") else ''
        note = f'<p class="slide-note">{lines(slide["note"])}</p>' if slide.get("note") else ''
        extra = ''
        if kind == 'example' and slide.get('example'):
            e = slide['example']
            extra = f'<div class="example-layout"><div><article class="mail" aria-label="虛構郵件示例"><div class="mail-title">虛構郵件示例</div><div class="mail-head"><p><strong>寄件者</strong> {esc(e.get("from", ""))}</p><p><strong>主旨</strong> {esc(e.get("subject", ""))}</p></div><div class="mail-body">{lines(e.get("body", ""))}</div></article><p class="example-caption">此郵件為情境示例，郵件中的文字不提供操作連結。</p></div><div>{bullet_html}</div></div>'
            bullet_html = ''
        if kind == 'flow' and slide.get('flow'):
            extra = '<ol class="flow">' + ''.join(f'<li>{lines(step)}</li>' for step in slide['flow']) + '</ol>'
        if kind == 'scenario' and slide.get('scenario'):
            q = slide['scenario']
            answer = int(q.get('correct', 0))
            options = ''.join(f'<button class="scenario-option" type="button" data-answer="{j}" aria-pressed="false"><span class="letter">{chr(65+j)}</span><span>{lines(option)}</span></button>' for j, option in enumerate(q.get('options', [])))
            extra = f'<div class="scenario" data-correct="{answer}" data-explanation="{esc(q.get("explanation", ""))}"><h2>{lines(q.get("question", ""))}</h2><div class="scenario-options">{options}</div><p class="scenario-result" role="status" hidden></p></div>'
        heading_title = lines(slide['title'])
        inner = f'<h1 tabindex="-1">{heading_title}</h1>{lead}{extra}{bullet_html}{note}'
        if kind == 'cover':
            inner = f'<div>{inner}</div><div class="cover-mark" aria-hidden="true">@</div>'
        hidden_attr = ' aria-hidden="true"' if i else ''
        section_kind = 'flow-slide' if kind == 'flow' else kind
        sections.append(f'<section class="slide {esc(section_kind)}{" active" if i == 0 else ""}" id="{sid}" aria-label="第 {i+1} 張，共 {len(slides)} 張：{title}"{hidden_attr}><div class="slide-top"><p class="eyebrow">{esc(slide.get("kicker", "釣魚郵件辨識與帳號防護"))}</p><span class="slide-id">{i+1:02d} / {len(slides):02d}</span></div><div class="slide-copy">{inner}</div>{slide_footer(slide, source_map)}</section>')
        toc.append(f'<li><a href="#{sid}" data-goto="{i}"><span>{i+1:02d}</span>{title}</a></li>')
    body = f'''<noscript><style>.slide{{display:flex!important}}</style><p class="no-js">此瀏覽器未啟用 JavaScript。以下顯示全部投影片，仍可閱讀與列印。</p></noscript><main class="deck-main" id="main">{''.join(sections)}</main>
<div class="deck-controls" aria-label="投影片導覽"><div class="progress" id="progress"></div><div class="row"><button id="toc-open" type="button" aria-haspopup="dialog">目錄</button><button class="print-button" id="print-all" type="button">列印全部</button><span class="shortcut">← → 翻頁 · Home / End</span></div><div class="control-center"><button id="prev" type="button" aria-label="上一張投影片">← 上一張</button><span id="counter" aria-live="polite">1 / {len(slides)}</span><button id="next" type="button" aria-label="下一張投影片">下一張 →</button></div></div>
<dialog id="toc" aria-labelledby="toc-title"><div class="dialog-head"><h2 id="toc-title">簡報目錄</h2><button id="toc-close" type="button" aria-label="關閉目錄">關閉 ×</button></div><ol class="toc-list">{''.join(toc)}</ol></dialog>'''
    script = r'''<script>
(()=>{'use strict';const slides=[...document.querySelectorAll('.slide')],prev=document.getElementById('prev'),next=document.getElementById('next'),counter=document.getElementById('counter'),progress=document.getElementById('progress'),toc=document.getElementById('toc');let index=0;
function go(n,focus=false){index=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.setAttribute('aria-hidden',String(i!==index));});prev.disabled=index===0;next.disabled=index===slides.length-1;counter.textContent=`${index+1} / ${slides.length}`;progress.style.width=((index+1)/slides.length*100)+'%';const hash='#'+slides[index].id;if(location.hash!==hash){history.replaceState(null,'',hash)}window.scrollTo({top:0,behavior:'instant'});if(focus)slides[index].querySelector('h1').focus({preventScroll:true});}
function fromHash(){const n=slides.findIndex(s=>'#'+s.id===location.hash);go(n<0?0:n)}
prev.addEventListener('click',()=>go(index-1,true));next.addEventListener('click',()=>go(index+1,true));document.getElementById('toc-open').addEventListener('click',()=>toc.showModal());document.getElementById('toc-close').addEventListener('click',()=>toc.close());document.getElementById('print-all').addEventListener('click',()=>window.print());
toc.querySelectorAll('[data-goto]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();toc.close();go(Number(a.dataset.goto),true)}));toc.addEventListener('click',e=>{if(e.target===toc){const r=toc.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)toc.close()}});
document.addEventListener('keydown',e=>{if(toc.open||e.ctrlKey||e.metaKey||e.altKey||/^(INPUT|TEXTAREA|SELECT|BUTTON|A|SUMMARY)$/.test(e.target.tagName)||e.target.isContentEditable)return;const keys={ArrowRight:index+1,ArrowDown:index+1,PageDown:index+1,ArrowLeft:index-1,ArrowUp:index-1,PageUp:index-1,Home:0,End:slides.length-1};if(e.key in keys){e.preventDefault();go(keys[e.key],true)}else if(e.key===' '){e.preventDefault();go(index+(e.shiftKey?-1:1),true)}});
document.querySelectorAll('.scenario').forEach(q=>{q.querySelectorAll('.scenario-option').forEach(b=>b.addEventListener('click',()=>{const correct=Number(q.dataset.correct),chosen=Number(b.dataset.answer),result=q.querySelector('.scenario-result');q.querySelectorAll('.scenario-option').forEach(x=>{const j=Number(x.dataset.answer);x.classList.toggle('correct',j===correct);x.classList.toggle('wrong',j===chosen&&chosen!==correct);x.setAttribute('aria-pressed',String(j===chosen))});result.hidden=false;result.classList.toggle('wrong',chosen!==correct);result.textContent=(chosen===correct?'判讀正確。':'請查看判讀依據。')+' '+q.dataset.explanation}));});window.addEventListener('hashchange',fromHash);fromHash();})();
</script>'''
    return document('互動簡報', body, 'slides', script, 'deck-body')


def render_wiki(pages, source_map):
    index = ''.join(f'<a href="#{ident(p["id"])}"><span class="source-id">{esc(p["id"])}</span>{esc(p["title"])}</a>' for p in pages)
    entries = []
    for p in pages:
        content = ''
        for b in p.get('body', []):
            refs = ''.join(f'<a href="#source-{ident(s)}">{esc(s)}</a>' for s in b.get('source_ids', []))
            locator = b.get('locator', '')
            if isinstance(locator, dict):
                locator = '；'.join(str(key) + '：' + str(value) for key, value in locator.items())
            elif isinstance(locator, list):
                locator = '；'.join(str(item) for item in locator)
            locator_html = f'<span class="locator">原文定位：{esc(locator)}</span>' if locator else ''
            content += f'<section><h3>{esc(b.get("heading", ""))}</h3><p class="body-text">{lines(b.get("text", ""))}</p><div class="inline-refs">{refs}{locator_html}</div></section>'
        related = ''.join(f'<a href="#{ident(r)}">{esc(r)}　{esc(next((x["title"] for x in pages if x["id"] == r), ""))}</a>' for r in p.get('related', []))
        entries.append(f'<article class="wiki-entry" id="{ident(p["id"])}"><p class="eyebrow">{esc(p["id"])} / Wiki 條目</p><h2>{esc(p["title"])}</h2><p class="summary">{lines(p.get("summary", ""))}</p>{content}<div class="related">延伸閱讀　{related or "返回目錄"}</div><details><summary>本條目來源</summary>{source_refs(p.get("source_ids", []), source_map)}</details></article>')
    sources = []
    for sid, s in source_map.items():
        retrieved = s.get('retrieved_at', s.get('retrieved_at_utc', s.get('retrieved_at_local', '詳見來源清單')))
        url = s.get('url', '')
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">閱讀原始來源 ↗</a>' if str(url).startswith(('https://','http://')) else ''
        card = s.get('evidence_card', {})
        summary = card.get('summary', '') if isinstance(card, dict) else ''
        summary_html = f'<p class="source-summary">{lines(summary)}</p>' if summary else ''
        sources.append(f'<article class="source-item" id="source-{ident(sid)}"><p class="source-id">{esc(sid)}</p><h3>{esc(s.get("title", sid))}</h3><p>{esc(s.get("publisher", ""))} · 來源紀錄時間：{esc(retrieved)}</p>{summary_html}<p>{link}</p></article>')
    body = f'''<main class="wrap" id="main"><div class="page-intro"><p class="eyebrow">Knowledge, with provenance</p><h1>釣魚防護 Wiki</h1><p>查閱概念、確認行動依據。每個條目連回原始出處，也能從簡報返回對應知識。</p></div><div class="wiki-toolbar"><div class="search-field"><label for="wiki-search">搜尋 Wiki 條目（本機全文篩選，不會呼叫即時 LLM）</label><input type="search" id="wiki-search" placeholder="例如：多因素、誤點、通報" autocomplete="off"></div><div class="search-count" id="search-count" aria-live="polite">{len(pages)} 個條目</div></div><div class="wiki-layout"><aside class="wiki-index" aria-label="Wiki 目錄"><h2>條目目錄</h2>{index}<a href="#source-list">來源清單 ↗</a></aside><div><div id="wiki-entries">{''.join(entries)}</div><p class="empty-search" id="empty-search" hidden>沒有符合的條目。請縮短關鍵字，或改用「密碼」「驗證」「釣魚」。</p><section class="source-section" id="source-list"><p class="eyebrow">Selected references</p><h2>來源清單</h2><p class="muted">來源 ID 連接精選引用卡、Wiki 條目與每張投影片。來源資訊見 <a href="sources/manifest.json">manifest.json</a>，內容摘要與定位見 <a href="sources/evidence-cards.json">引用卡</a>。</p>{''.join(sources)}</section></div></div><footer class="page-footer"><span>Wiki 內容由 LLM 根據來源引用整理；瀏覽器提供離線閱讀與搜尋。</span><a href="evidence.html">查看驗證方式與來源對照 →</a></footer></main>'''
    script = r'''<script>(()=>{'use strict';const input=document.getElementById('wiki-search'),entries=[...document.querySelectorAll('.wiki-entry')],count=document.getElementById('search-count'),empty=document.getElementById('empty-search');function filter(){const terms=input.value.trim().toLocaleLowerCase().split(/ +/).filter(Boolean);let n=0;entries.forEach(e=>{e.hidden=!terms.every(t=>e.textContent.toLocaleLowerCase().includes(t));if(!e.hidden)n++});count.textContent=n+' 個條目';empty.hidden=n!==0}input.addEventListener('input',filter);function reveal(){let id=location.hash.slice(1);try{id=decodeURIComponent(id)}catch{}if(id&&document.getElementById(id)?.classList.contains('wiki-entry')){input.value='';filter()}}window.addEventListener('hashchange',reveal);reveal()})();</script>'''
    return document('Wiki 知識庫', body, 'wiki', script)


def render_index(pages, slides, source_map):
    body = f'''<main class="wrap" id="main"><section class="hero"><div><p class="eyebrow">LLM Wiki × 互動簡報</p><h1>釣魚郵件辨識<br>與帳號防護</h1><p class="lead">辨識可疑郵件、確認查證管道，並採取適當的帳號保護與復原措施。每項重點都能回查來源。</p><div class="row" style="margin-top:32px"><a class="button" href="slides.html">瀏覽簡報 <span aria-hidden="true">→</span></a><a class="button secondary" href="wiki.html">開啟 Wiki</a></div></div><div class="hero-art" aria-hidden="true"><span class="art-top">PHISHING DEFENSE · ACCOUNT SECURITY</span><span class="huge">@</span><div class="art-bottom">看見警訊<br>回到可信管道<br><span>再採取行動</span></div></div></section><div class="stats" aria-label="專案內容"><div class="stat"><strong>{len(source_map):02d}</strong><span>已收錄的可追溯來源</span></div><div class="stat"><strong>{len(pages):02d}</strong><span>互相連結的 Wiki 條目</span></div><div class="stat"><strong>{len(slides):02d}</strong><span>互動簡報投影片</span></div></div><section class="section"><div class="section-header"><h2>閱讀與查證</h2><span class="muted">所有頁面可直接離線開啟</span></div><a class="destination" href="slides.html"><span class="number">01</span><div><h3>互動簡報</h3><p>查看郵件示例與情境判讀。支援目錄、前後翻頁、方向鍵與列印。</p></div><span class="arrow" aria-hidden="true">↗</span></a><a class="destination" href="wiki.html"><span class="number">02</span><div><h3>LLM Wiki 閱讀介面</h3><p>搜尋概念、追蹤條目間的連結，從每個行動建議返回可靠來源。</p></div><span class="arrow" aria-hidden="true">↗</span></a><a class="destination" href="evidence.html"><span class="number">03</span><div><h3>流程與驗證</h3><p>查看內容編纂流程、來源對照與專案驗證方式。</p></div><span class="arrow" aria-hidden="true">↗</span></a></section><aside class="notice">各條目以來源 ID 連結精選引用卡與原始出處。專案說明與驗證方式見 <a href="README.md">README</a> 及 <a href="evidence.html">流程與驗證</a>。</aside><footer class="page-footer"><span>釣魚郵件辨識與帳號防護 · 繁體中文資安知識庫</span><a href="README.md">閱讀專案說明 →</a></footer></main>'''
    return document('知識庫首頁', body)


def workflow_graph():
    steps = [
        ('來源整理', '官方出處與精選引用'), ('來源核對', '格式與引用定位'),
        ('Ingest', '來源索引與資料庫'), ('LLM Wiki', '編纂與交叉連結'),
        ('檢索', '問題與相關條目'), ('內容稿', '依 Wiki 整理重點'),
        ('內容檢查', '引用一致・文字清楚'), ('HTML', '渲染已核對內容'),
        ('瀏覽器', '響應式版面與操作'), ('發布', '內容與驗證文件'),
    ]
    nodes = ''.join(f'<li class="workflow-node"><span class="step-num">{i+1:02d}</span><strong>{esc(title)}</strong><small>{esc(detail)}</small></li>' for i, (title, detail) in enumerate(steps))
    return f'''<section class="section" style="padding-top:25px" aria-labelledby="workflow-title"><div class="section-header"><h2 id="workflow-title">內容編纂與驗證流程</h2><span class="muted">更新內容，核對來源，驗證呈現</span></div><figure class="workflow-figure"><p class="workflow-prelude">引用卡、Wiki 條目與簡報以來源 ID 串聯，更新時檢查受影響內容。</p><ol class="workflow-graph" aria-label="由來源整理到發布的十個步驟">{nodes}</ol><div class="workflow-loops"><p><span class="loop-arrow" aria-hidden="true">↶</span><strong>來源不符或依據不足</strong> → 回到來源整理／核對，補齊後更新 Wiki。</p><p><span class="loop-arrow" aria-hidden="true">↶</span><strong>引用或表達未通過</strong> → 回到 Wiki／內容稿；版面或操作失敗 → 回到 HTML。</p></div><figcaption>流程規格與驗證範圍見專案文件。<a href="docs/workflow.md">查看流程說明與 Mermaid 原始碼 →</a></figcaption></figure></section>'''


def render_evidence(root, pages, slides, source_map):
    docs = sorted((root / 'docs').glob('*.md'))
    menu, rendered_docs = [], []
    for i, file in enumerate(docs):
        text = file.read_text(encoding='utf-8-sig')
        title = next((x.lstrip('#').strip() for x in text.splitlines() if x.startswith('# ')), file.stem)
        anchor = 'doc-' + ident(file.stem)
        menu.append(f'<a href="#{anchor}">{esc(title)}</a>')
        rendered_docs.append(f'<article class="document" id="{anchor}"><p class="eyebrow">Document {i+1:02d}</p><h2>{esc(title)}</h2><a class="doc-file" href="docs/{esc(file.name)}">原始 Markdown：{esc(file.name)}</a><pre>{esc(text)}</pre></article>')
    rows = []
    for s in slides:
        wrefs = ''.join(f'<a href="wiki.html#{ident(w)}">{esc(w)}</a>' for w in s.get('wiki_ids', []))
        srefs = ''.join(f'<a href="wiki.html#source-{ident(x)}">{esc(x)}</a>' for x in s.get('source_ids', []))
        rows.append(f'<tr><td><a href="slides.html#{ident(s["id"])}">{esc(s["id"])}</a></td><td>{esc(s["title"])}</td><td>{wrefs or "專案紀錄"}</td><td>{srefs or "專案紀錄"}</td></tr>')
    body = f'''<main class="wrap" id="main"><div class="page-intro"><p class="eyebrow">Process & validation</p><h1>流程與驗證</h1><p>查看內容編纂流程、投影片與 Wiki 的對照，以及專案驗證方式。</p></div><div class="evidence-links"><a href="README.md">專案說明</a><a href="sources/manifest.json">來源清單 JSON</a><a href="sources/evidence-cards.json">精選引用卡</a><a href="wiki/pages.json">Wiki 結構資料</a><a href="slides/slides.json">簡報結構資料</a></div>{workflow_graph()}<section class="section" style="padding-top:25px"><div class="section-header"><h2>投影片 × Wiki × 來源</h2><span class="muted">{len(slides)} 張投影片的追溯索引</span></div><div class="table-scroll"><table><thead><tr><th scope="col">投影片</th><th scope="col">主題</th><th scope="col">Wiki 條目</th><th scope="col">來源 ID</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section><section class="section"><h2>專案文件與驗證紀錄</h2><nav class="evidence-menu" aria-label="專案文件目錄">{''.join(menu)}</nav>{''.join(rendered_docs) or '<p>專案文件尚未加入。</p>'}</section><footer class="page-footer"><span>本頁由專案資料產生；檢查範圍與結果見各驗證文件。</span><a href="index.html">回到知識庫首頁 →</a></footer></main>'''
    return document('流程與驗證', body, 'evidence')


def load_array(path):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(value, dict):
        for key in ('sources', 'pages', 'slides', 'items'):
            if key in value:
                value = value[key]
                break
    if not isinstance(value, list):
        raise ValueError(f'{path}: expected a JSON array')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    pages = load_array(root / 'wiki' / 'pages.json')
    slides = load_array(root / 'slides' / 'slides.json')
    sources = load_array(root / 'sources' / 'manifest.json')
    if not pages or not slides or not sources:
        raise ValueError('Wiki, slides and source manifest must not be empty')
    for name, records in [('Wiki', pages), ('slides', slides), ('sources', sources)]:
        ids = [r['id'] for r in records]
        if len(set(ids)) != len(ids):
            raise ValueError(f'Duplicate IDs in {name}')
    source_map = {s['id']: s for s in sources}
    cards_path = root / 'sources' / 'evidence-cards.json'
    if cards_path.exists():
        for card in load_array(cards_path):
            if card.get('id') in source_map:
                source_map[card['id']]['evidence_card'] = card
    wiki_ids = {p['id'] for p in pages}
    for s in slides:
        if set(s.get('wiki_ids', [])) - wiki_ids:
            raise ValueError(f'{s["id"]}: unknown Wiki reference')
        if set(s.get('source_ids', [])) - source_map.keys():
            raise ValueError(f'{s["id"]}: unknown source reference')
    results = {
        'index.html': render_index(pages, slides, source_map),
        'slides.html': render_slides(slides, source_map),
        'wiki.html': render_wiki(pages, source_map),
        'evidence.html': render_evidence(root, pages, slides, source_map),
    }
    for name, content in results.items():
        (root / name).write_text(content, encoding='utf-8', newline='\n')
    print(json.dumps({'rendered': list(results), 'sources': len(sources), 'wiki_pages': len(pages), 'slides': len(slides)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
