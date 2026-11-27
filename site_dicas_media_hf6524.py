"""HF65.24: validadores de material editorial finalizado."""
import base64
import io
from PIL import Image, ImageOps


def preparar_arte(raw: bytes) -> str:
    if not raw or len(raw) > 12_000_000:
        raise ValueError('Imagem vazia ou maior que 12 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as src:
            if src.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError('Formato inválido. Envie PNG, JPG ou WEBP.')
            src.verify()
        with Image.open(io.BytesIO(raw)) as src:
            img = ImageOps.exif_transpose(src)
            img.thumbnail((1280,1280))
            if img.mode in ('RGBA','LA') or (img.mode=='P' and 'transparency' in img.info):
                rgb = Image.new('RGB',img.size,'white')
                rgb.paste(img.convert('RGBA'),mask=img.convert('RGBA').getchannel('A'))
            else:
                rgb=img.convert('RGB')
            for quality in (85,72,60,45):
                out=io.BytesIO()
                rgb.save(out,format='JPEG',quality=quality,optimize=True)
                if out.tell()<=320_000:
                    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode('ascii')
            raise ValueError('Imagem complexa demais para salvar no documento. Tente uma versão reduzida.')
    except (OSError,Image.DecompressionBombError) as exc:
        raise ValueError('Imagem inválida ou muito grande.') from exc


def validar_video(raw: bytes):
    if not raw or len(raw)>80_000_000:
        raise ValueError('Envie MP4 de até 80 MB.')
    if b'ftyp' not in raw[:64]:
        raise ValueError('Arquivo não parece ser MP4 válido.')
    return True
