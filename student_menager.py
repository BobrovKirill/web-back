# main.py или student_manager.py

import csv
from typing import List, Optional
from sqlalchemy import create_engine, String, Integer, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.exc import SQLAlchemyError


# 1. Модель данных
class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    faculty: Mapped[str] = mapped_column(String(100), nullable=False)
    course: Mapped[str] = mapped_column(String(150), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self):
        return f"<Student {self.last_name} {self.first_name} | {self.course} | {self.grade}>"


# 2. Класс для основных операций
class StudentManager:
    def __init__(self, db_url: str = "sqlite:///students.db"):
        self.engine = create_engine(db_url, echo=False)
        # Создаём таблицы (если их ещё нет)
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return Session(self.engine)

    # 3. Заполнение данными из CSV
    def load_from_csv(self, csv_path: str = "students.csv") -> int:
        count = 0
        with self.get_session() as session:
            try:
                with open(csv_path, encoding="utf-8") as f:
                    reader = csv.reader(f, delimiter=",")
                    next(reader)  # пропускаем заголовок, если он есть

                    for row in reader:
                        # Обрабатываем возможные пустые строки и лишние пробелы
                        if len(row) < 5:
                            continue
                        last_name = row[0].strip()
                        first_name = row[1].strip()
                        faculty = row[2].strip()
                        course = row[3].strip()
                        try:
                            grade = int(row[4].strip())
                        except ValueError:
                            continue

                        student = Student(
                            last_name=last_name,
                            first_name=first_name,
                            faculty=faculty,
                            course=course,
                            grade=grade
                        )
                        session.add(student)
                        count += 1

                session.commit()
                return count
            except Exception as e:
                session.rollback()
                print(f"Ошибка при загрузке CSV: {e}")
                return 0

    # 4. Методы выборки

    def get_students_by_faculty(self, faculty_name: str) -> List[Student]:
        with self.get_session() as session:
            stmt = select(Student).where(Student.faculty == faculty_name)
            return session.scalars(stmt).all()

    def get_unique_courses(self) -> List[str]:
        with self.get_session() as session:
            stmt = select(Student.course.distinct())
            return session.scalars(stmt).all()

    def get_students_with_low_grade_by_course(
        self, course_name: str, threshold: int = 30
    ) -> List[Student]:
        """* Дополнительное задание"""
        with self.get_session() as session:
            stmt = (
                select(Student)
                .where(Student.course == course_name)
                .where(Student.grade < threshold)
                .order_by(Student.grade)
            )
            return session.scalars(stmt).all()

    def get_average_grade_by_faculty(self, faculty_name: str) -> Optional[float]:
        with self.get_session() as session:
            stmt = (
                select(func.avg(Student.grade))
                .where(Student.faculty == faculty_name)
            )
            result = session.scalar(stmt)
            return round(float(result), 2) if result is not None else None


# Пример использования
if __name__ == "__main__":
    manager = StudentManager()

    # Загружаем данные один раз (потом можно закомментировать)
    inserted = manager.load_from_csv("students.csv")
    print(f"Загружено студентов: {inserted}")

    # Примеры запросов
    print("\nСтуденты факультета РЭФ:")
    for s in manager.get_students_by_faculty("РЭФ"):
        print(f"  {s.last_name} {s.first_name} — {s.course} — {s.grade}")

    print("\nУникальные курсы:")
    print(", ".join(manager.get_unique_courses()))

    print("\nСтуденты на 'Мат. Анализ' с оценкой < 30:")
    low = manager.get_students_with_low_grade_by_course("Мат. Анализ", 30)
    for s in low:
        print(f"  {s.last_name} {s.first_name} — {s.grade}")

    print("\nСредний балл по факультету АВТФ:")
    avg = manager.get_average_grade_by_faculty("АВТФ")
    print(avg if avg is not None else "нет данных")