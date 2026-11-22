import logging
import os
import uuid
from dataclasses import dataclass

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

MB = 1024 * 1024

# Limites do plano gratuito do Cloudinary. Se o plano mudar, ajustar aqui.
LIMITE_IMAGEM = 10 * MB
LIMITE_VIDEO = 100 * MB
LIMITE_DOCUMENTO = 10 * MB

# Extensão -> (resource_type no Cloudinary, limite em bytes).
# O tipo vem desta lista, e não de "auto", para barrar HTML, SVG, executáveis etc.
TIPOS_PERMITIDOS: dict[str, tuple[str, int]] = {
    ".jpg": ("image", LIMITE_IMAGEM),
    ".jpeg": ("image", LIMITE_IMAGEM),
    ".png": ("image", LIMITE_IMAGEM),
    ".webp": ("image", LIMITE_IMAGEM),
    ".heic": ("image", LIMITE_IMAGEM),
    ".mp4": ("video", LIMITE_VIDEO),
    ".mov": ("video", LIMITE_VIDEO),
    ".webm": ("video", LIMITE_VIDEO),
    ".3gp": ("video", LIMITE_VIDEO),
    ".pdf": ("raw", LIMITE_DOCUMENTO),
    ".doc": ("raw", LIMITE_DOCUMENTO),
    ".docx": ("raw", LIMITE_DOCUMENTO),
}


@dataclass
class MidiaValidada:
    arquivo: UploadFile
    nome_arquivo: str
    extensao: str
    resource_type: str


@dataclass
class MidiaEnviada:
    url: str
    public_id: str
    resource_type: str
    nome_arquivo: str


def _tamanho(arquivo: UploadFile) -> int:
    if arquivo.size is not None:
        return arquivo.size

    posicao = arquivo.file.tell()
    arquivo.file.seek(0, os.SEEK_END)
    tamanho = arquivo.file.tell()
    arquivo.file.seek(posicao)
    return tamanho


def validar_midias(medias: list[UploadFile]) -> list[MidiaValidada]:
    """Valida todos os arquivos antes de qualquer envio.

    Responde 415 para tipo não permitido e 413 para tamanho acima do limite.
    Partes do formulário sem nome de arquivo (campo vazio) são ignoradas.
    """
    validadas = []

    for media in medias:
        if not media.filename:
            continue

        nome = os.path.basename(media.filename)
        extensao = os.path.splitext(nome)[1].lower()

        if extensao not in TIPOS_PERMITIDOS:
            permitidas = ", ".join(sorted(TIPOS_PERMITIDOS))
            raise HTTPException(
                status_code=415,
                detail=f"Tipo de arquivo não permitido: {nome}. Extensões aceitas: {permitidas}.",
            )

        resource_type, limite = TIPOS_PERMITIDOS[extensao]

        if _tamanho(media) > limite:
            raise HTTPException(
                status_code=413,
                detail=f"O arquivo {nome} excede o limite de {limite // MB} MB.",
            )

        validadas.append(
            MidiaValidada(
                arquivo=media,
                nome_arquivo=nome[:255],
                extensao=extensao,
                resource_type=resource_type,
            )
        )

    return validadas


async def enviar_midia(midia: MidiaValidada) -> MidiaEnviada:
    """Envia um arquivo ao Cloudinary sem bloquear o loop de eventos.

    O public_id é aleatório: o nome original pode identificar um paciente e
    não deve aparecer na URL. Em arquivos "raw" o public_id leva a extensão,
    que o Cloudinary não acrescenta sozinho.
    """
    public_id = f"notificacoes/{uuid.uuid4().hex}"
    if midia.resource_type == "raw":
        public_id += midia.extensao

    midia.arquivo.file.seek(0)

    resultado = await run_in_threadpool(
        cloudinary.uploader.upload,
        midia.arquivo.file,
        resource_type=midia.resource_type,
        public_id=public_id,
        overwrite=False,
    )

    return MidiaEnviada(
        url=resultado["secure_url"],
        public_id=resultado["public_id"],
        resource_type=resultado.get("resource_type", midia.resource_type),
        nome_arquivo=midia.nome_arquivo,
    )


async def remover_midias(itens: list[tuple[str | None, str | None]]) -> None:
    """Apaga arquivos do Cloudinary a partir de pares (public_id, resource_type).

    Falhas são registradas em log e não interrompem quem chamou: o registro no
    banco já foi tratado e um erro aqui não deve desfazer isso.
    """
    for public_id, resource_type in itens:
        if not public_id:
            continue

        try:
            await run_in_threadpool(
                cloudinary.uploader.destroy,
                public_id,
                resource_type=resource_type or "image",
                invalidate=True,
            )
        except Exception:
            logger.exception("Falha ao remover %s (%s) do Cloudinary", public_id, resource_type)
