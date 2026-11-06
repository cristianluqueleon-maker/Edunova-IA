# EduNova AI — MVP inicial

Aplicación web ejecutable: login de administrador, estudiantes (crear/eliminar), registro de notas, configuración de escala/periodos, carga y extracción de texto de documentos PDF/DOCX/TXT y resumen opcional usando OpenAI. Datos demo ficticios.

## Ejecutar
1. Instala Docker y Docker Compose.
2. Copia `.env.example` como `.env` y cambia `SESSION_SECRET` y `ADMIN_PASSWORD`.
3. Añade `OPENAI_API_KEY` en `.env` si quieres habilitar resumen IA.
4. Corre `docker compose up --build -d`.
5. Abre `http://localhost:8000`; credenciales del `.env`.
6. Health check: `/health`.

## Dominio
En un VPS, apunta el DNS A del dominio a su IP y sirve la app tras Caddy/Nginx con HTTPS. No publiques el servicio en HTTP directamente para producción. Cambia el middleware de sesión para `https_only=True`, guarda secretos seguros y configura backups. El zip no se instala en el dominio sin acceso al VPS y DNS.

## Importante: alcance
Esta es una base MVP para iterar, no una versión lista para datos reales de menores. No implementa aún multiinstitución real, gestión completa de roles, matrícula, docentes/acudientes, asistencia, boletines, PIAR, auditoría, CSRF/rate limits, recuperación de contraseña, ni hardening de producción. La IA resume documentos; no extrae reglas estructuradas con citas ni las aplica automáticamente. Mantén datos ficticios hasta una revisión de seguridad y privacidad. La sesión inicial usa cookie firmada; revisa configuración HTTPS antes de producción.
