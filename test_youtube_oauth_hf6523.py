"""Testes offline HF65.23: sem rede nem acesso ao YouTube real."""
import unittest
from unittest.mock import patch, Mock
from cryptography.fernet import Fernet
import site_youtube_oauth_service as oauth
import site_youtube_multicanal_service as videos


class TestYoutubeOAuth(unittest.TestCase):
    def setUp(self):
        self.conf = {"client_id": "demo.apps.googleusercontent.com", "client_secret": "secret-local",
                     "redirect_uri": oauth.REDIRECT_URI_OFICIAL,
                     "fernet_key": Fernet.generate_key().decode()}
        self.canal = "UC" + "A" * 22

    def test_url_e_estado(self):
        self.assertTrue(oauth.configurado(self.conf))
        with patch.object(oauth.time, "time", return_value=1700000000):
            state = oauth.gerar_estado(self.conf)
            url = oauth.url_autorizacao(self.conf)
        self.assertTrue(oauth.verificar_estado(state, self.conf, now=1700000300))
        self.assertFalse(oauth.verificar_estado(state, self.conf, now=1700000601))
        self.assertFalse(oauth.verificar_estado(state[:-1]+"a", self.conf, now=1700000300))
        self.assertIn('youtube.upload', url)
        self.assertIn('youtube.readonly', url)
        self.assertNotIn('secret-local', url)

    def test_validacao_canal_e_criptografia(self):
        state = oauth.gerar_estado(self.conf)
        result_token = Mock(status_code=200)
        result_token.json.return_value = {"access_token":"access-internal","refresh_token":"refresh-secret"}
        result_token.raise_for_status = Mock()
        def mocked_get(url, **kw):
            r=Mock(status_code=200)
            r.raise_for_status=Mock()
            if "userinfo" in url:
                r.json.return_value = {"email":"alphafesti@gmail.com", "email_verified": True}
            else:
                r.json.return_value = {"items":[{"id":self.canal,"snippet":{"customUrl":"@AlphafestItatiba2026","title":"AlphaFest"}}]}
            return r
        with patch.object(oauth.requests, "post", return_value=result_token), patch.object(oauth.requests, "get", side_effect=mocked_get):
            registro = oauth.trocar_codigo_e_validar("authorization-code",state,self.conf)
        self.assertNotIn("refresh-secret", str(registro))
        self.assertEqual(registro["channel_id"], self.canal)
        self.assertEqual(oauth.credenciais_upload(registro, self.conf)["refresh_token"], "refresh-secret")

    def test_bloqueia_canal_incorreto(self):
        state = oauth.gerar_estado(self.conf)
        result_token = Mock(); result_token.json.return_value = {"access_token":"access","refresh_token":"refresh"}
        def mocked_get(url, **kw):
            r=Mock()
            if "userinfo" in url: r.json.return_value={"email":"alphafesti@gmail.com","email_verified":True}
            else: r.json.return_value={"items":[{"id":self.canal,"snippet":{"customUrl":"@OutroCanal","title":"Outro"}}]}
            return r
        with patch.object(oauth.requests, "post", return_value=result_token), patch.object(oauth.requests, "get", side_effect=mocked_get):
            with self.assertRaisesRegex(oauth.ErroYoutubeOAuth, "não corresponde"):
                oauth.trocar_codigo_e_validar("authorization-code", state, self.conf)

    def test_bloqueia_upload_para_outro_canal(self):
        with patch.object(videos, "_youtube_access_token", return_value="fake-access"), \
             patch.object(oauth, "conferir_canal_no_token", return_value=False), \
             patch.object(videos.requests, "post") as remote:
            with self.assertRaisesRegex(RuntimeError,"Upload bloqueado"):
                videos.publicar_video_privado_youtube(b"mp4",{"title":"Dica"}, {},expected_channel_id=self.canal)
            remote.assert_not_called()

    def test_config_errada_nao_autoriza(self):
        self.assertFalse(oauth.configurado({"client_id":"x", "client_secret":"y", "fernet_key":"invalido", "redirect_uri":oauth.REDIRECT_URI_OFICIAL}))
        self.assertFalse(oauth.configurado({**self.conf, "redirect_uri":"https://exemplo.com/"}))

if __name__=="__main__":
    unittest.main()
