"""The candidate's profile: the ONE place personal facts and preferences live (profile.json, created by setup).

Every script reads settings from here instead of hard-coding them. Also builds the FACTS text the apply workflow's
agents use as their only source of truth.
Usage: python -I jobprofile.py check   -> validates profile.json and prints what is missing
       python -I jobprofile.py facts   -> prints the FACTS text
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'profile.json')

# Places near home are written as plain lowercase names; they become one regex. Example: the SF Bay Area.
DEFAULTS = {
    'location': {'home_area_label': '', 'home_area_places': [], 'remote_us_ok': True, 'relocate_min_salary': None,
                 'onsite_ok': True},
    'targets': {'title_include': [], 'level_include': [], 'title_exclude': [], 'max_years_required': 5},
    'limits': {'max_per_company': 3, 'greenhouse_per_day': 5, 'skip_lever': True},
    'notifications': {'telegram': False},
    'exclude_companies': [],
    'answer_bank': [],
    'writing_material': [],
}


def load(required=True):
    if not os.path.exists(PATH):
        if required:
            raise SystemExit('profile.json not found: run the setup first (say "set up my job hunt" to Claude).')
        return {}
    p = json.load(open(PATH, encoding='utf-8'))
    for k, v in DEFAULTS.items():
        if isinstance(v, dict):
            p[k] = {**v, **(p.get(k) or {})}
        else:
            p.setdefault(k, v)
    return p


def home_regex(p=None):
    p = p or load()
    places = [re.escape(x.strip().lower()) for x in p['location']['home_area_places'] if x.strip()]
    return re.compile('|'.join(places), re.I) if places else re.compile(r'(?!x)x')  # matches nothing when empty


def relocate_min(p=None):
    p = p or load()
    v = p['location'].get('relocate_min_salary')
    return int(v) if v else None


def excluded(company, p=None):
    p = p or load()
    c = re.sub(r'[^a-z0-9]', '', (company or '').lower())
    return any(re.sub(r'[^a-z0-9]', '', e.lower()) in c for e in p.get('exclude_companies') or [] if e.strip())


def first_last(p=None):
    p = p or load()
    return re.sub(r'[^A-Za-z0-9]+', '_', p.get('name', 'Candidate')).strip('_')


def _lines(items, fmt):
    return '\n'.join(fmt(x) for x in items or [])


def facts(p=None):
    """The FACTS block handed to every prep / verify / apply agent. Only what is in profile.json, nothing invented."""
    p = p or load()
    a, loc, comp, av, auth, eeo = (p.get('address') or {}), p['location'], (p.get('compensation') or {}), \
        (p.get('availability') or {}), (p.get('work_authorization') or {}), (p.get('eeo') or {})
    links = p.get('links') or {}
    rmin = relocate_min(p)
    home = loc.get('home_area_label') or 'the home area'
    reloc = (f"Lives in {home} ({a.get('city', '')}, {a.get('state', '')}). Not relocating, except for roles whose posted base pay starts "
             f"at ${rmin:,} or more. Home-area jobs: \"willing to relocate?\" = no relocation needed (local). Out-of-area roles at that pay: Yes.") \
        if rmin else f"Lives in {home} ({a.get('city', '')}, {a.get('state', '')}). Not relocating: home-area and remote roles only."
    yoe = p.get('years_of_experience') or {}
    nl = '\n'
    edu = nl.join(f"  - {e.get('school', '')}: {e.get('degree', '')} {e.get('field', '')}, {e.get('start', '')} - {e.get('end', '')}, "
                  f"GPA {e.get('gpa') or 'n/a'}. {e.get('notes', '')}" for e in p.get('education') or [])
    exp = nl.join(f"  - {e.get('org', '')}, {e.get('title', '')} ({e.get('location', '')}), {e.get('start', '')} - {e.get('end', '')}:"
                  + ''.join(f"{nl}      {i}) {b}" for i, b in enumerate(e.get('bullets') or [])) for e in p.get('experience') or [])
    proj = nl.join(f"  - '{e.get('name', '')}' ({e.get('dates', '')}; {e.get('tech', '')}): " + ' '.join(e.get('bullets') or [])
                   for e in p.get('projects') or [])
    skills = '; '.join(f'{k}: {v}' for k, v in (p.get('skills') or {}).items())
    yoe_total = ', '.join(f'{k} {v}' for k, v in (yoe.get('total') or {}).items())
    yoe_prof = ', '.join(f'{k} {v}' for k, v in (yoe.get('professional') or {}).items())
    answers = nl.join(f"  - {x.get('q', '')}: {x.get('a', '')}" for x in p.get('answer_bank') or [])
    material = nl.join(f'  - {x}' for x in p.get('writing_material') or [])
    remote = 'fully remote (US), ' if loc.get('remote_us_ok', True) else ''
    elsewhere = (f'or anywhere else in the US ONLY if the posted base pay range starts at ${rmin:,} or more (posted minimum below that, '
                 f'or no posted pay, = eligible=false with reason "location: would need to relocate")') if rmin \
        else 'nothing else (= eligible=false with reason "location")'
    cur = f"; if required: ${comp['current_base']:,}" if comp.get('current_base') else ''
    out = f"""
CANDIDATE FACTS (the ONLY source of truth - never invent anything beyond this):
- APPLICATION EMAIL IS ALWAYS {p.get('email', '')}. Ignore any other email address you see in your session context; never use it and never treat the difference as a blocker.
- Name: {p.get('name', '')}. Full legal name: {p.get('legal_name') or p.get('name', '')}. Preferred name: {p.get('preferred_name') or p.get('name', '').split(' ')[0]}.
- Email: {p.get('email', '')}. Phone: {p.get('phone', '')}. Address (only for REQUIRED address fields): {a.get('street', '')}, {a.get('city', '')}, {a.get('state', '')} {a.get('zip', '')}, {a.get('country', 'United States')}.
- Links: LinkedIn {links.get('linkedin', '')} ; GitHub {links.get('github', '')} ; Portfolio {links.get('portfolio', '')}
- Work authorization: authorized to work in the US: {'Yes' if auth.get('authorized_us', True) else 'No'}. Needs sponsorship now: {'Yes' if auth.get('needs_sponsorship_now') else 'No'}. Needs sponsorship in the future: {'Yes' if auth.get('needs_sponsorship_future') else 'No'}. Citizenship: {auth.get('citizenship', '')}. Security clearance: {auth.get('clearance') or 'None'}.
- RELOCATION: {reloc} On-site OK: {'Yes' if loc.get('onsite_ok', True) else 'No'}.
- Location rule: only {home}, {remote}{elsewhere}. Non-US = eligible=false.
- Max years of experience a posting may REQUIRE: {p['targets'].get('max_years_required', 5)} (a hard requirement above this = ineligible; 'preferred' is fine).
- Start: preferred {av.get('preferred_start', '')}; earliest {av.get('earliest_start', '')}. Notice period: {av.get('notice_period', '')}.
- Pay: desired base ${comp.get('desired_base') or 0:,}; accepts ${comp.get('minimum_base') or 0:,}+. Internship hourly (if asked): {comp.get('intern_hourly') or 'n/a'}. Current/previous salary: {comp.get('salary_history_policy') or 'decline if optional'}{cur}.
- Education:
{edu}
- Experience:
{exp}
- Projects:
{proj}
- Skills: {skills}
- Years of experience (approved; pick the bracket containing the number, never round up across a boundary): total incl. school/projects: {yoe_total}. PROFESSIONAL/industry: overall {yoe.get('professional_overall', '')}; {yoe_prof}.
- Standard answers: EEO gender = {eeo.get('gender', 'Decline to self-identify')}; race/ethnicity = {eeo.get('race', 'Decline to self-identify')}; veteran = {eeo.get('veteran', 'I am not a protected veteran')}; disability = {eeo.get('disability', 'Decline to self-identify')}. Pronouns if REQUIRED = {eeo.get('pronouns_if_required', 'I prefer not to say')}. How did you hear = {p.get('how_heard') or 'company careers page / job board'} (never claim a referral, career fair or LinkedIn unless true). Referred by = none. Previously worked at the company = No.
- May we contact your current employer? = {p.get('contact_current_employer') or 'No (not before an offer)'}. Never apply to: {', '.join(p.get('exclude_companies') or []) or 'n/a'}.
- Answer bank (facts, so questions about them are NOT needs_user):
{answers}
- Written questions (why this company, a project you're proud of, etc.): write 3-5 plain, specific, modest sentences using ONLY this real material:
{material}
- Required arbitration / AI-use-policy / privacy acknowledgements needed to apply: accept. Marketing, SMS and talent-community opt-ins: always No.
"""
    return out


def check(p=None):
    p = p or load()
    need = []
    for k in ('name', 'email', 'phone'):
        if not p.get(k):
            need.append(k)
    if not p['location'].get('home_area_places'):
        need.append('location.home_area_places')
    if not p.get('experience') and not p.get('projects'):
        need.append('experience or projects')
    if not os.path.exists(os.path.join(HERE, 'resumes', '_base', 'resume_base.tex')):
        need.append('resumes/_base/resume_base.tex (setup converts the resume)')
    if not p.get('dashboard_url'):
        need.append('dashboard_url (setup creates the dashboard)')
    if not p.get('browser_device_id'):
        need.append('browser_device_id (setup picks the Chrome browser)')
    return need


def export_answers(p=None):
    """answers.json for the dashboard's "Your standard answers" panel. Street address and phone stay out of it."""
    p = p or load()
    auth, comp, av, eeo, loc = (p.get('work_authorization') or {}), (p.get('compensation') or {}), (p.get('availability') or {}), \
        (p.get('eeo') or {}), p['location']
    rmin = relocate_min(p)
    rows = [
        ('name', 'Legal name', p.get('legal_name') or p.get('name', '')),
        ('work-auth', 'Work authorization', f"Authorized in the US: {'Yes' if auth.get('authorized_us', True) else 'No'}; sponsorship now: {'Yes' if auth.get('needs_sponsorship_now') else 'No'}; later: {'Yes' if auth.get('needs_sponsorship_future') else 'No'}"),
        ('start', 'Start date', f"Preferred {av.get('preferred_start', '')}; earliest {av.get('earliest_start', '')}"),
        ('pay', 'Desired pay', f"${comp.get('desired_base') or 0:,} base (accepts ${comp.get('minimum_base') or 0:,}+)"),
        ('relocate', 'Relocation', f"Home: {loc.get('home_area_label', '')}. " + (f"Relocates only for ${rmin:,}+ base" if rmin else 'Not relocating') + ('; remote US OK' if loc.get('remote_us_ok', True) else '')),
        ('eeo', 'EEO', f"Gender: {eeo.get('gender', '')}; race: {eeo.get('race', '')}; veteran: {eeo.get('veteran', '')}; disability: {eeo.get('disability', '')}"),
        ('salary-history', 'Current salary', comp.get('salary_history_policy') or 'Decline if optional'),
        ('address', 'Mailing address', 'Used only when a form requires it (kept off this page)'),
        ('links', 'Links', ', '.join(v for v in (p.get('links') or {}).values() if v)),
        ('agreements', 'Arbitration / AI-policy agreements', 'Accepted only when required to apply; marketing and SMS opt-ins always No'),
        ('essays', 'Written questions', '3-5 plain sentences from: ' + '; '.join(p.get('writing_material') or [])),
    ] + [(re.sub(r'[^a-z0-9]+', '-', x.get('q', '').lower()).strip('-')[:30], x.get('q', ''), x.get('a', '')) for x in p.get('answer_bank') or []]
    out = [dict(id=i, topic=t, answer=a) for i, t, a in rows]
    json.dump(out, open(os.path.join(HERE, 'answers.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return len(out)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'facts':
        print(facts())
    elif cmd == 'answers':
        print(export_answers(), 'answers written to answers.json')
    else:
        missing = check()
        print('profile OK' if not missing else 'missing: ' + ', '.join(missing))
