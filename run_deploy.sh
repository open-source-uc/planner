# falta implementar

# Este archivo no debe ser ejecutado a mano, ni tampoco es necesario en el desarrollo.
# Solamente debe ser ejecutado directamente en el servidor de producción, recurrentemente y de forma automática a través del archivo `update.sh`.

# TODO: Docker debe enviar todos sus mensajes syslog a la IP entregada por arquitectura en el puerto entregado por arquitectura.
# - Agrega al script `run-deploy.sh` lo siguiente para la configuración de syslog:
#  docker run -it --log-driver=syslog --log-opt syslog-address=udp://localhost:514 prashant23/ubuntu-java:sample-jdbc-project bash
