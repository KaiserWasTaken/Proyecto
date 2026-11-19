# Optimización del IR

`optimizar` devuelve el IR optimizado y una descripción por instrucción
eliminada. Las reglas de redundancia y sobrescritura pueden desactivarse
independientemente.

La equivalencia comprende el estado final de todos los dispositivos y las
salidas de `GET_STATE`, `LIST_DEVICES`, `NOTIFY` y `SEND_EMAIL` en el mismo
orden. La VM sí emite eventos `SET_STATE` para mostrar las acciones; estos
eventos intermedios se excluyen de la comparación de equivalencia.

## Reglas y justificación

1. **Asignación redundante:** si una asignación previa al mismo dispositivo
   establece el mismo estado y no hay barrera intermedia, se elimina la
   posterior. El estado ya es igual y no existe observación intermedia.
2. **Asignación sobrescrita:** si una asignación posterior al mismo dispositivo
   establece un estado distinto sin barrera intermedia, se eliminan las
   anteriores sobrescritas. Ninguna salida lee ese estado previo y la última
   asignación determina el estado final.

Las asignaciones a otros dispositivos no son barreras. `GET_STATE`, `COMPARE`,
`LIST_DEVICES`, `NOTIFY`, `SEND_EMAIL` y `HALT` sí lo son; no se eliminan ni
reordenan. Por ejemplo, en `ENCENDER led1; CONSULTAR led1; APAGAR led1`,
eliminar la primera asignación cambiaría la consulta. Tampoco se elimina
en presencia de una notificación o correo intermedios: son efectos externos
y deben conservar su posición respecto a los cambios de estado.

## Flujo de control

Un bloque comienza al inicio, en cada destino de salto y después de un
`JUMP_IF_FALSE`; el salto termina el bloque y nunca se elimina. No se combinan
asignaciones entre bloques: el cuerpo de un condicional puede no ejecutarse.
Tras eliminar instrucciones se reajustan los destinos absolutos; si se eliminó
un destino, el salto apunta a la siguiente instrucción conservada.
