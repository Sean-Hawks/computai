import io
import os
import unittest
from unittest import mock

from tests import helpers


class HomeTestCase(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.m = helpers.load()
        self.env = mock.patch.dict(os.environ, self.sb.env())
        self.env.start()
        self.addCleanup(self.env.stop)


class HomeEntry(HomeTestCase):
    def test_noninteractive_home_is_a_readonly_guide_in_both_languages(self):
        for lang, title in [('en', 'Monthly recap'), ('zh', '做月報圖卡')]:
            result = self.sb.run('--lang', lang)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(title, result.stdout)
            for command in ('computai recap', 'computai --live', 'computai --web', 'computai --doctor'):
                self.assertIn(command, result.stdout)
            self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(os.path.exists(self.sb.config))
        self.assertFalse(os.path.exists(self.sb.data))
        with mock.patch('sys.stdout', new_callable=io.StringIO), mock.patch('sys.stdin.isatty', return_value=False), \
                mock.patch.object(self.m, 'ensure_config') as config, \
                mock.patch.object(self.m, 'open_ledger') as ledger, \
                mock.patch.object(self.m, 'sync') as sync, \
                mock.patch.object(self.m, 'check_update_in_background') as updates:
            self.assertEqual(self.m.main([]), 0)
        for operation in (config, ledger, sync, updates):
            operation.assert_not_called()

    def test_menu_is_visible_before_any_configuration_or_collection(self):
        output = io.StringIO()
        with mock.patch('sys.stdout', output), mock.patch.object(output, 'isatty', return_value=True), \
                mock.patch('sys.stdin.isatty', return_value=True), \
                mock.patch('builtins.input', side_effect=lambda _: self.assertIn('computai recap', output.getvalue()) or 'q'), \
                mock.patch.object(self.m, 'ensure_config') as config, \
                mock.patch.object(self.m, 'open_ledger') as ledger:
            self.assertEqual(self.m.main([]), 0)
        config.assert_not_called()
        ledger.assert_not_called()

    def test_all_six_choices_dispatch_existing_actions_and_recap_intent(self):
        for number, action in enumerate(('live', 'create', 'web', 'analyze', 'doctor', 'setup'), 1):
            output = io.StringIO()
            with mock.patch('sys.stdout', output), mock.patch.object(output, 'isatty', return_value=True), \
                    mock.patch('sys.stdin.isatty', return_value=True), \
                    mock.patch('sys.stderr.isatty', return_value=False), \
                    mock.patch('builtins.input', return_value=str(number)), \
                    mock.patch.object(self.m, 'run', return_value=0) as run:
                self.assertEqual(self.m.main(['--lang', 'zh', '--no-open', '--no-sync']), 0)
            args = run.call_args.args[0]
            self.assertTrue(getattr(args, action))
            self.assertTrue(args.home_entry)
            self.assertEqual(args.recap_entry, action == 'create')
            self.assertTrue(args.no_open)
            self.assertTrue(args.no_sync)
            if action == 'web':
                self.assertEqual(args.web, '127.0.0.1:8765')

    def test_enter_invalid_input_and_interrupt_are_predictable(self):
        answers = iter(['something', ''])
        said = []
        self.assertEqual(self.m.choose_home(ask=lambda _: next(answers), out=said.append), 'live')
        self.assertIn('Choose 1–6', said[-1])
        for end in ('0', ' Q ', KeyboardInterrupt(), EOFError()):
            with mock.patch('builtins.input', **({'side_effect': end} if isinstance(end, BaseException) else {'return_value': end})):
                self.assertIsNone(self.m.choose_home(out=lambda _: None))

    def test_explicit_actions_bypass_menu_including_zero_valued_options(self):
        commands = (['--live'], ['--summary'], ['--json'], ['recap'], ['--web'], ['--tailscale'],
                    ['--paths'], ['--claude-limits'], ['--recap', '0'], ['--wrapped'], ['--payback', '0'],
                    ['--month'], ['--set', 'general.lang=zh'], ['--by', 'day'])
        for argv in commands:
            with mock.patch('sys.stdout', new_callable=io.StringIO), \
                    mock.patch('sys.stdin.isatty', return_value=True), \
                    mock.patch('sys.stderr.isatty', return_value=False), \
                    mock.patch.object(self.m, 'choose_home') as home, \
                    mock.patch.object(self.m, 'run', return_value=0) as run:
                self.assertEqual(self.m.main(argv), 0)
            home.assert_not_called()
            if '--paths' not in argv:
                run.assert_called_once()

    def test_home_monitor_opens_without_plan_questions(self):
        args = self.m.parse_args(['--live', '--no-sync', '--no-intro'])
        args.home_entry = True
        db = self.m.open_ledger(':memory:')
        self.addCleanup(db.close)
        with mock.patch.object(self.m, 'ask_plans_once') as plans, \
                mock.patch.object(self.m, 'run_live', return_value=0) as live:
            self.assertEqual(self.m.run(args, db), 0)
        plans.assert_not_called()
        live.assert_called_once_with(5.0, 60, False)

    def test_home_browser_launch_and_no_open_are_forwarded(self):
        for no_open in (False, True):
            args = self.m.parse_args(['--web'] + (['--no-open'] if no_open else []))
            args.home_entry = True
            db = self.m.open_ledger(':memory:')
            with mock.patch.object(self.m, 'serve_web', return_value=0) as web:
                self.assertEqual(self.m.run(args, db), 0)
            self.assertEqual(web.call_args.kwargs, {'tailscale': False, 'launch': not no_open})

    def test_home_layout_respects_display_width_for_traditional_chinese(self):
        for lang in ('en', 'zh'):
            self.m.set_lang(lang)
            for width in (40, 72, 100):
                text = self.m.render_home(width, interactive=True)
                self.assertTrue(all(self.m.vlen(line) <= width for line in text.splitlines()), text)
                self.assertIn('computai recap', text)


class MonitorHelp(HomeTestCase):
    def test_help_works_while_waiting_and_dismisses_without_restarting_collector(self):
        output = io.StringIO()
        with mock.patch.object(self.m.threading, 'Thread') as thread, \
                mock.patch.object(self.m, 'read_key', side_effect=['h', '\t', '?', '\x1b', 'q']), \
                mock.patch('sys.stdin.isatty', return_value=False), mock.patch('sys.stdout', output), \
                mock.patch.object(self.m, 'sync') as sync:
            self.assertEqual(self.m.run_live(1, 0, intro=False), 0)
        thread.assert_called_once()
        sync.assert_not_called()
        self.assertEqual(output.getvalue().count('ComputAI · Help'), 2)
        self.assertIn('computai recap', output.getvalue())
        self.assertIn('\x1b[?25h\x1b[?1049l', output.getvalue())

    def test_help_key_during_intro_is_not_lost(self):
        output = io.StringIO()
        with mock.patch.object(self.m.threading, 'Thread'), \
                mock.patch.object(self.m, 'config_theme', return_value='cyber'), \
                mock.patch.object(self.m, 'read_key', side_effect=['h', 'q']), \
                mock.patch('sys.stdin.isatty', return_value=False), mock.patch('sys.stdout', output):
            self.assertEqual(self.m.run_live(1, 0), 0)
        self.assertIn('ComputAI · Help', output.getvalue())

    def test_help_keeps_exit_hint_in_small_terminal(self):
        self.m.set_lang('zh')
        for width, height in ((40, 12), (72, 24), (100, 40)):
            text = self.m.render_live_help(width, height)
            self.assertLessEqual(len(text.splitlines()), height - 1)
            self.assertTrue(all(self.m.vlen(line) <= width for line in text.splitlines()))
            self.assertIn('q 離開', text.splitlines()[-1])


class HomeBrowser(HomeTestCase):
    def test_browser_opens_after_binding_to_the_actual_loopback_port(self):
        import http.server
        for launch in (False, True):
            output = io.StringIO()
            addresses = []
            real_server = http.server.ThreadingHTTPServer.__init__

            def bind(server, *args, **kwargs):
                real_server(server, *args, **kwargs)
                addresses.append(server.server_address)

            def open_browser(url):
                self.assertEqual(url, 'http://127.0.0.1:%d/' % addresses[0][1])
                self.assertIn(url, output.getvalue())
                return True

            with mock.patch.object(http.server.ThreadingHTTPServer, '__init__', bind), \
                    mock.patch.object(http.server.ThreadingHTTPServer, 'serve_forever', side_effect=KeyboardInterrupt), \
                    mock.patch.object(self.m.threading, 'Thread'), mock.patch('sys.stdout', output), \
                    mock.patch('webbrowser.open', side_effect=open_browser) as browser:
                self.assertEqual(self.m.serve_web('127.0.0.1:0', 1, 0, launch=launch), 0)
            self.assertEqual(browser.call_count, int(launch))


@unittest.skipIf(os.name == 'nt', 'POSIX pseudo-terminal')
class HomeTerminal(HomeTestCase):
    def test_real_terminal_can_go_from_home_to_monthly_page(self):
        import errno
        import fcntl
        import pty
        import select
        import subprocess
        import sys
        import struct
        import termios
        import time

        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
        process = subprocess.Popen([sys.executable, helpers.SCRIPT, '--lang', 'zh', '--no-open', '--no-sync'],
                                   stdin=slave, stdout=slave, stderr=slave, env=self.sb.env())
        os.close(slave)
        output = bytearray()
        chosen = False
        deadline = time.monotonic() + 20
        try:
            while time.monotonic() < deadline:
                if not select.select([master], [], [], 0.1)[0]:
                    continue
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if not chosen and '選擇 [1] >'.encode() in output:
                    self.assertFalse(os.path.exists(self.sb.config))
                    self.assertFalse(os.path.exists(self.sb.data))
                    os.write(master, b'2\n')
                    chosen = True
            self.assertEqual(process.wait(timeout=3), 0, output.decode('utf-8'))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
        text = output.decode('utf-8')
        self.assertTrue(chosen)
        self.assertIn('做月報圖卡', text)
        self.assertIn('下載 PNG', text)
        self.assertNotIn('Traceback', text)
        self.assertTrue(os.path.isfile(os.path.join(self.sb.data, 'creator.html')))


if __name__ == '__main__':
    unittest.main()
