from prisma import Prisma

# Prisma gestiona la conexión a la base de datos
# al recibir `DATABASE_URL` como variable de entorno mediante el .env
# (Si, prisma es así de mágico)

prisma = Prisma(auto_register=True)
