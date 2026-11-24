"""Exercise the real card against the real engine using a mock HA transport.
Requires optional playwright and Chromium; no live Home Assistant required.
"""
import asyncio
import shutil
from datetime import datetime
import importlib.util
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('engine',ROOT/'custom_components/family_quests/engine.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
NOW=datetime.fromisoformat('2026-11-17T18:00:00+01:00')


async def main():
    e=m.Engine()
    for name in ['Maty','Momo']:e.save_person({'name':name},NOW,'setup')
    a,b=e.s['people']
    e.save_task({'name':'Prezliecť do pyžama','icon':'👕','points':2,'group':'Večer'},NOW,'setup')
    tid=next(iter(e.s['tasks']))
    e.save_task({'name':'Umytie zubov','icon':'🦷','points':2,'group':'Večer'},NOW,'setup')
    e.save_reward({'name':'Spoločný výlet','cost':20,'icon':'🌳'},NOW,'setup')
    e.save_reward({'name':'Čítanie rozprávky','kind':'task','task':tid,'icon':'📖'},NOW,'setup')
    e.tick(NOW)
    is_admin=True
    calls=[]
    async def transport(msg):
        calls.append(msg)
        if msg['type']=='family_quests/action':
            assert msg['expected_version']==e.s['version']
            e.apply(msg['action'],msg['data'],NOW,'browser',is_admin)
            e.s['version']+=1
        return e.snapshot(NOW,is_admin)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True, executable_path=shutil.which("chromium"), args=["--no-process-singleton", "--no-zygote", "--single-process"])
        page=await browser.new_page(viewport={'width':1024,'height':1365})
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        await page.expose_function('transport',transport)
        await page.set_content('<html><body style="margin:0;background:#0b1014;padding:24px"><div style="max-width:800px;margin:auto" id="host"></div></body></html>')
        await page.add_script_tag(content=(ROOT/'custom_components/family_quests/frontend/family-quests-card.js').read_text())
        await page.evaluate('''(timestamp)=>{Date.now=()=>timestamp; window.mockHass={states:{},callWS:window.transport}; window.mount=(mode)=>{document.querySelector('#host').innerHTML='';window.card=document.createElement('family-quests-card');card.setConfig({mode});document.querySelector('#host').appendChild(card);card.hass=mockHass;};mount('child');}''',int(NOW.timestamp()*1000))
        await page.get_by_role('heading',name='Maty',exact=True).wait_for()
        await page.get_by_role('button',name='Splniť: Prezliecť do pyžama').click()
        await page.wait_for_function("card._data.people[0].balance===2")
        assert e.balance(a)==2
        await page.get_by_role('button',name='Odmeny',exact=True).click()
        await page.get_by_role('button',name='Chcem odmenu',exact=True).click()
        await page.wait_for_function("card._data.requests.length===1")
        await page.get_by_role('button',name='Môj symbol',exact=True).click()
        await page.locator('input[name=symbol]').fill('🐴')
        await page.locator('input[name=unit]').fill('Koníky')
        await page.get_by_role('button',name='Uložiť',exact=True).click()
        await page.wait_for_function("card._data.people[0].symbol==='🐴'")
        assert e.balance(a)==2
        await page.get_by_role('button',name='Úlohy',exact=True).click()
        await page.screenshot(path='/tmp/family-child.png',full_page=True)
        await page.evaluate("mount('admin')")
        await page.get_by_role('button',name='+2',exact=True).click()
        await page.wait_for_function("card._data.people[0].balance===4")
        await page.get_by_role('button',name='História',exact=True).click()
        await page.locator('button[data-action=reverse-adjustment]').click()
        await page.wait_for_function("card._data.people[0].balance===2")
        await page.get_by_role('button',name='Dnes',exact=True).click()
        page.on('dialog',lambda dialog:dialog.accept())
        await page.get_by_role('button',name='↶ Vrátiť',exact=True).click()
        await page.wait_for_function("card._data.people[0].balance===0")
        assert next(iter(e.s['requests'].values()))['status']=='cancelled'
        await page.get_by_role('button',name='Úlohy',exact=True).click()
        await page.get_by_role('button',name='+ Nová úloha',exact=True).click()
        await page.locator('input[name=name]').fill('Vyniesť smeti')
        await page.locator('select[name=mode]').select_option('first')
        await page.get_by_role('button',name='Uložiť',exact=True).click()
        await page.get_by_role('heading',name='Vyniesť smeti',exact=True).wait_for()
        assert len(e.s['tasks'])==3
        await page.get_by_role('button',name='Účastníci',exact=True).click()
        await page.get_by_role('button',name='+ Pridať účastníka',exact=True).click()
        await page.locator('input[name=name]').fill('Marek')
        await page.get_by_role('button',name='Uložiť',exact=True).click()
        await page.wait_for_function("card._data.people.length===3")
        await page.get_by_role('button',name='Odmeny',exact=True).click()
        await page.get_by_role('button',name='+ Nová odmena',exact=True).click()
        await page.locator('input[name=name]').fill('Kino')
        await page.locator('input[name=cost]').fill('30')
        await page.get_by_role('button',name='Uložiť',exact=True).click()
        await page.get_by_role('heading',name='Kino',exact=True).wait_for()
        await page.get_by_role('button',name='Dnes',exact=True).click()
        await page.screenshot(path='/tmp/family-admin.png',full_page=True)
        await page.set_viewport_size({'width':390,'height':844})
        await page.evaluate("mount('child')")
        await page.get_by_role('heading',name='Maty',exact=True).wait_for()
        assert await page.evaluate('document.documentElement.scrollWidth<=390')
        await page.screenshot(path='/tmp/family-mobile.png',full_page=True)
        is_admin=False
        await page.evaluate("mount('admin')")
        await page.get_by_text('Rodičovský panel je dostupný iba správcovi',exact=False).wait_for()
        assert await page.locator('button[data-action=adjust]').count()==0
        assert not errors,errors
        print('PASS: child complete, reward request, symbols; parent exact undo, adjustments, create task/person/reward; mobile overflow; non-admin gate; no JS exceptions.')
        await browser.close()

if __name__=='__main__':asyncio.run(main())
