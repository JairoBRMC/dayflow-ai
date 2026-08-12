## Modelo de datos

### User
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID / int | Identificador único |
| email | string | Email del usuario, único |
| hashed_password | string | Contraseña cifrada |
| created_at | datetime | Fecha de registro |

### Task
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID / int | Identificador único |
| title | string | Título de la tarea |
| description | string (opcional) | Detalle adicional |
| status | enum | pending / in_progress / done |
| priority | enum | low / medium / high |
| due_date | date (opcional) | Fecha límite |
| user_id | FK → User | Propietario de la tarea |

### Event
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID / int | Identificador único |
| title | string | Título del evento |
| start_time | datetime | Inicio |
| end_time | datetime | Fin |
| user_id | FK → User | Propietario del evento |

### ChatMessage
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID / int | Identificador único |
| role | enum | user / assistant |
| content | text | Contenido del mensaje |
| created_at | datetime | Fecha del mensaje |
| user_id | FK → User | Propietario de la conversación |

### Relaciones
- Un **User** tiene muchas **Task** (1:N)
- Un **User** tiene muchos **Event** (1:N)
- Un **User** tiene muchos **ChatMessage** (1:N)

> Esquema inicial, sujeto a cambios a medida que avance el desarrollo (ej. futura entidad `Goal` para agrupar tareas por objetivo).

![Diagrama ER](./docs/er-diagram.png)