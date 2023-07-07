# Uso del servicio de login del backend

## CAS

Es necesario correr un servidor CAS para usar la funcionalidad de autenticación del backend.
El `.env` indica el URL del servidor de CAS, que en el entorno de desarrollo es `localhost:3004`.
Luego, hay que correr un servidor de CAS en `localhost:3004`.
Esto se puede hacer corriendo el siguiente comando *dentro del container* (esto es importante para que el servidor de backend tenga acceso al servidor CAS):

    npx --yes cas-server-mock --database=$PWD/cas-mock/data/cas-mock-users.json

Notar que el servidor mock CAS es *muy básico*.
Por ejemplo, introducir un usuario inexistente produce una excepción en el servidor de mock CAS,
cortando la conexión al backend, produciendo un error 502.

Esto se hace automaticamente al correr el proyecto desde VSCode.
