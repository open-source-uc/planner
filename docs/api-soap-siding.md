
# Detalles importantes sobre la API SOAP de Siding

## Correcciones al spec `.wsdl`

El archivo `.wsdl` tal como es proveido no funciona con otro cliente que no sea `SoapClient` de PHP.

En particular, hay dos problemas con el `.wsdl` original:

- Se hace referencia a un tipo `stringArray` que no se define.

No soy experto en WSDL, pero este tipo es compatible con algo como lo siguiente:

```xml
<xsd:complexType name="stringArray">
    <xsd:all>
        <xsd:element name="strings" type="tns:stringsList" maxOccurs="1" minOccurs="1">
        </xsd:element>
    </xsd:all>
</xsd:complexType>

<xsd:complexType name="stringsList">
    <xsd:sequence>
        <xsd:element name="string" type="xsd:string" maxOccurs="unbounded"
            minOccurs="0">
        </xsd:element>
    </xsd:sequence>
</xsd:complexType>
```

- El atributo `location` del servicio esta mal definido, le falta un `/`:

Original:

```xml
<soap:address location="https://intrawww.ing.puc.cl/siding/ws/ServiciosPlanner_test1" />
```

Arreglado:

```xml
<soap:address location="https://intrawww.ing.puc.cl/siding/ws/ServiciosPlanner_test1/" />
```

## Observaciones de la API

- El endpoint `getConcentracionCursos` lanza un XML invalido para combinaciones invalidas de major-minor-titulo (pero arroja status 200 OK). Tambien lo lanza para algunas combinaciones validas (eg. `C2020-M073-N206-40006`).
- Las combinaciones invalidas entregan una lista vacia en `getMallaSugerida`.
- Hay majors sin minors asociados? `M186 - Major en Ingenieria Civil - Track en Diseno y Construccion de Obras`. Es version `Vs.02` y ademas sirve para curriculum `C2013`, `C2020` y `C2022`.
