# API Request Reference

All routes below are exposed under the `/api/v1` prefix. Unless stated otherwise, request bodies may be sent as `application/json`, `application/x-www-form-urlencoded`, or `multipart/form-data` thanks to the shared request parser.

## Authentication

### `POST /auth/login`
```json
{
  "username": "string",
  "password": "string"
}
```

### `POST /auth/login/json`
Same payload as `/auth/login`, but JSON-only convenience endpoint.

### `POST /auth/refresh`
```json
{
  "refresh_token": "string"
}
```

### `POST /auth/logout`
```json
{
  "refresh_token": "string"
}
```

## Users

### `POST /users`
```json
{
  "name": "string",
  "username": "string",
  "password": "string",
  "role": "admin | coach | user"
}
```

### `PUT /users/{user_id}`
```json
{
  "name": "string?",
  "username": "string?",
  "password": "string?",
  "is_active": true
}
```
All fields are optional. Only provide values you want to change.

## Permissions

### `POST /permissions/assign`
```json
{
  "user_id": 0,
  "permission": "permission_code"
}
```

### `POST /permissions/revoke`
```json
{
  "user_id": 0,
  "permission": "permission_code"
}
```
`permission` must be one of the enumerated permission codes defined in the system.

## Schools

### `POST /schools`
```json
{
  "name": "string"
}
```

### `PUT /schools/{school_id}`
```json
{
  "name": "string?"
}
```

## Batches

### `POST /batches`
```json
{
  "name": "string",
  "school_id": 0,
  "coach_id": 0
}
```
`coach_id` is optional. The referenced coach must belong to the same school.

### `PUT /batches/{batch_id}`
```json
{
  "name": "string?",
  "school_id": 0,
  "coach_id": 0
}
```
Provide only the fields you need to change. `school_id` and `coach_id` are validated for consistency.

## Students

### `POST /students`
```json
{
  "name": "string",
  "age": 0,
  "school_id": 0,
  "coach_id": 0,
  "batch_id": 0
}
```
`school_id`, `coach_id`, and `batch_id` are optional, but when supplied they must reference existing entities and belong to the same school/batch context.

### `PUT /students/{student_id}`
```json
{
  "name": "string?",
  "age": 0,
  "school_id": 0,
  "coach_id": 0,
  "batch_id": 0
}
```
Each field is optional; validation rules match the create request.

### `PUT /students/{student_id}/change_batch`
```json
{
  "new_batch_id": 0
}
```
Moves a student to another batch and automatically reconciles upcoming session results.

## Coaches

### `POST /coaches`
```json
{
  "username": "string",
  "name": "string",
  "password": "string",
  "school_id": 0
}
```
`school_id` is optional; when provided it must exist.

### `PUT /coaches/{coach_id}`
```json
{
  "username": "string?",
  "name": "string?",
  "password": "string?",
  "school_id": 0
}
```
All fields optional. Password updates will be re-hashed automatically.

## Physical Assessments

### `POST /physical/sessions/`
```json
{
  "coach_id": 0,
  "school_id": 0,
  "batch_id": 0,
  "date_of_session": "YYYY-MM-DD",
  "student_count": 0
}
```
If `batch_id` is supplied, the coach and school are validated against the batch and `student_count` must match (or will be coerced to) the batch size.

### `POST /physical/sessions/create-with-results`
```json
{
  "coach_id": 0,
  "school_id": 0,
  "batch_id": 0,
  "date_of_session": "YYYY-MM-DD",
  "results": [
    {
      "student_id": 0,
      "discipline": "string",
      "curl_up": 0,
      "push_up": 0,
      "sit_and_reach": 0.0,
      "one_km_run_min": 0,
      "one_km_run_sec": 0
    }
  ],
  "admin_override": false
}
```
`results` must contain unique `student_id` entries that belong to the batch (unless an administrator sends `admin_override=true`). Numeric fields are validated to be non-negative.

### `PUT /physical/sessions/{session_id}`
```json
{
  "coach_id": 0,
  "school_id": 0,
  "batch_id": 0,
  "date_of_session": "YYYY-MM-DD",
  "student_count": 0
}
```
All fields optional; cross-entity relationships are checked for consistency.

### `PUT /physical/results/{result_id}`
```json
{
  "discipline": "string",
  "curl_up": 0,
  "push_up": 0,
  "sit_and_reach": 0.0,
  "one_km_run_min": 0,
  "one_km_run_sec": 0,
  "is_present": true
}
```
Provide only the metrics you need to update. Leaving or setting all numeric values to zero will automatically mark the student as absent (`is_present=false`).
