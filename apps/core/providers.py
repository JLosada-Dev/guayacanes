"""
Constantes del aspect catch-all "Otros".

"Otros" es un aspect transversal: cualquier servicio del catálogo puede
recibir una denuncia con aspect_slug='other-issue' y el ciudadano
describe el problema en `custom_aspect_description`. No es un servicio
ni vive en BD — se valida por slug en el serializer.
"""
OTHER_ASPECT_SLUG = 'other-issue'
