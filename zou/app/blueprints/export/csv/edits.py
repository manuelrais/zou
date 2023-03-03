from flask_restful import Resource
from flask_jwt_extended import jwt_required
from slugify import slugify

from zou.app.services import (
    edits_service,
    projects_service,
    user_service,
    tasks_service,
    persons_service,
)
from zou.app.utils import csv_utils


class EditsCsvExport(Resource):
    @jwt_required()
    def get(self, project_id):
        """
        Export edits linked to a given project as csv.
        ---
        tags:
          - Export
        parameters:
          - in: path
            name: project_id
            required: True
            type: string
            format: UUID
            x-example: a24a6ea4-ce75-4665-a070-57453082c25
        responses:
            200:
                description: Edits exported as csv
        """
        self.task_type_map = tasks_service.get_task_type_map()
        self.task_status_map = tasks_service.get_task_status_map()
        self.persons_map = persons_service.get_persons_map()

        project = projects_service.get_project(project_id)
        self.check_permissions(project["id"])

        csv_content = []
        results = self.get_edits_data(project_id)
        metadata_infos = self.get_metadata_infos(project_id)
        validation_columns = self.get_validation_columns(results)
        headers = self.build_headers(metadata_infos, validation_columns)
        csv_content.append(headers)

        for result in results:
            result["project_name"] = project["name"]
            csv_content.append(
                self.build_row(result, metadata_infos, validation_columns)
            )

        file_name = "%s edits" % project["name"]
        return csv_utils.build_csv_response(csv_content, slugify(file_name))

    def check_permissions(self, project_id):
        user_service.check_project_access(project_id)
        user_service.block_access_to_vendor()

    def build_headers(self, metadata_infos, validation_columns):
        headers = ["Project", "Episode", "Name", "Description", "Time Spent"]

        metadata_headers = [name for (name, _) in metadata_infos]

        validation_assignations_columns = []
        for validation_column in validation_columns:
            validation_assignations_columns.append(validation_column)
            validation_assignations_columns.append("Assignations")

        return headers + metadata_headers + validation_assignations_columns

    def build_row(self, result, metadata_infos, validation_columns):
        row = [
            result["project_name"],
            result["episode_name"],
            result["name"],
            result["description"],
            self.get_time_spent(result),
        ]
        task_map = {}

        for task in result["tasks"]:
            task_status = self.task_status_map[task["task_status_id"]]
            task_type = self.task_type_map[task["task_type_id"]]
            task_map[task_type["name"]] = {}
            task_map[task_type["name"]]["short_name"] = task_status[
                "short_name"
            ]
            task_map[task_type["name"]]["assignees"] = ",".join(
                [
                    self.persons_map[person_id]["full_name"]
                    for person_id in task["assignees"]
                ]
            )

        for _, field_name in metadata_infos:
            result_metadata = result.get("data", {}) or {}
            row.append(result_metadata.get(field_name, ""))

        for column in validation_columns:
            if column in task_map:
                row.append(task_map[column]["short_name"])
                row.append(task_map[column]["assignees"])
            else:
                row.append("")
                row.append("")

        return row

    def get_edits_data(self, project_id):
        results = edits_service.get_edits_and_tasks({"project_id": project_id})
        return sorted(
            results,
            key=lambda edit: (edit["episode_name"], edit["name"]),
        )

    def get_validation_columns(self, results):
        task_type_map = {}

        for result in results:
            for task in result["tasks"]:
                task_type = self.task_type_map[task["task_type_id"]]
                task_type_map[task_type["name"]] = {
                    "name": task_type["name"],
                    "priority": task_type["priority"],
                }

        validation_columns = [
            task_type["name"]
            for task_type in sorted(
                task_type_map.values(),
                key=lambda task_type: (
                    task_type["priority"],
                    task_type["name"],
                ),
            )
        ]

        return validation_columns

    def get_metadata_infos(self, project_id):
        descriptors = [
            descriptor
            for descriptor in projects_service.get_metadata_descriptors(
                project_id
            )
            if descriptor["entity_type"] == "Edit"
        ]

        columns = [
            (descriptor["name"], descriptor["field_name"])
            for descriptor in descriptors
        ]

        return columns

    def get_time_spent(self, result):
        time_spent = 0
        for task in result["tasks"]:
            if task["duration"] is not None:
                time_spent += task["duration"]

        if time_spent > 0:
            time_spent = time_spent / 8.0 / 60.0

        return "%.2f" % time_spent
