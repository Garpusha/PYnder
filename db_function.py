import os.path
import configparser
import models as m
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker


def get_db_config(ini_file: str = "config.ini") -> str:
    """
    Функция читает из конфигурационного файла, по умолчанию config.ini
    :param ini_file: .ini filename with path if necessary, by default - config.ini
    :return: DSN string for sqlalchemy engine creation:
    postgresql://{db_user}:{db_pwd}@{db_ip}:{db_port}/{db_name}
    """

    if not os.path.exists(ini_file):
        print(f"Configuration file '{ini_file}' not found.")
        exit()

    config = configparser.ConfigParser()
    config.read(ini_file)
    try:
        db_ip = config.get("DataBase", "IP")
        db_port = config.get("DataBase", "Port")
        db_name = config.get("DataBase", "DBName")
        db_user = config.get("DataBase", "User")
        db_pwd = config.get("DataBase", "Password")
    except configparser.Error as error_msg:
        print(f"Error occurred. {error_msg}")
        exit()

    return f"postgresql://{db_user}:{db_pwd}@{db_ip}:{db_port}/{db_name}"


class PYnder_DB:
    def __init__(self, rebuild: bool):
        self.engine = sq.create_engine(get_db_config("config.ini"))
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        if rebuild:
            self.delete_structure()
            self.create_structure()

    def get_favorite(self, vk_owner_id_: str) -> list:
        """
        Метод возвращает список избранного
        :param vk_owner_id_: str Owner's VK ID
        :return: list of dicts {
            vk_id:str(50),
            first_name:str(20),
            last_name:str(20),
            city(20):str,
            sex:integer,
            birth_date:date,
            url:str,
            images[{'url':'image_1.jpg', likes: 5}, {'url':'image_2.jpg', likes: 3}, {'url':'image_3.jpg', likes: 15}]
            }
        """
        with self.session as db:
            # Reading data from tables
            owner_pk_ = self.get_pk(m.Owner.id, vk_owner_id_)
            if owner_pk_ == -1:
                return []
            my_query = db.query(
                m.Owner.id,
                m.VKUser.vk_id,
                m.VKUser.first_name,
                m.VKUser.last_name,
                m.VKUser.city,
                m.VKUser.sex,
                m.VKUser.birth_date,
                m.VKUser.url,
                m.Photo.url,
                m.Photo.likes,
            ).filter_by(id=owner_pk_)
            my_query = my_query.join(m.Favorite, m.Favorite.owner_id == m.Owner.id)
            my_query = my_query.join(m.VKUser, m.VKUser.id == m.Favorite.user_id)
            my_query = my_query.join(m.Photo, m.Photo.user_id == m.VKUser.id)
            result = my_query.all()
            favorite_dict = {}
            favorite_list = []
            vk_ids = []
            for element in result:
                f_vkid = element[1]
                if f_vkid not in vk_ids:
                    vk_ids.append(f_vkid)
                    favorite_dict["vk_id"] = element[1]
                    favorite_dict["first_name"] = element[2]
                    favorite_dict["last_name"] = element[3]
                    favorite_dict["city"] = element[4]
                    favorite_dict["sex"] = element[5]
                    favorite_dict[
                        "birth_date"
                    ] = f"{element[6].day}.{element[6].month}.{element[6].year}"
                    favorite_dict["url"] = element[7]
                    favorite_dict["images"] = [{"url": element[8], "likes": element[9]}]
                    favorite_list.append(favorite_dict.copy())
                else:
                    for index, item in enumerate(favorite_list):
                        if item["vk_id"] == f_vkid:
                            favorite_list[index]["images"].append(
                                {"url": element[8], "likes": element[9]}
                            )
                            break

            return favorite_list

    def get_pk(self, table_, id_: str) -> int:
        """
        Метод возвращает primary key для определенного VK ID
        :param table_ table object with parameter, e.g. m.VKUser.id
        :param id_: VK ID:
        :return: PK ID or -1 if not found
        """

        with self.session as db:
            my_query = db.query(table_).filter_by(vk_id=id_)
            if my_query.count() == 0:
                return -1
            else:
                return my_query.first()[0]

    def is_in_favorite(self, vk_user_id_: str, vk_owner_id_: str) -> bool:
        """
        Метод проверяет наличие пользователя ВК в избранном
        :param vk_user_id_: User's VK ID
        :param vk_owner_id_: Owner's VK ID
        :return: True if in Favorites, False otherwise
        """
        with self.session as db:
            user_pk_ = self.get_pk(m.VKUser.id, vk_user_id_)
            if user_pk_ == -1:
                return False
            my_query = db.query(m.Favorite.user_id).filter_by(user_id=user_pk_)
            if my_query.count() == 0:
                return False
            owner_pk_ = self.get_pk(m.Owner.id, vk_owner_id_)
            if owner_pk_ == -1:
                return False
            my_query = db.query(m.Favorite.owner_id).filter_by(owner_id=owner_pk_)
            if my_query.count() == 0:
                return False
            my_query = db.query(m.Favorite.owner_id, m.Favorite.owner_id).filter_by(
                user_id=user_pk_, owner_id=owner_pk_
            )
            if my_query.count() == 0:
                return False
            else:
                return True

    def delete_favorite(self, vk_user_id_: str, vk_owner_id_: str) -> bool:
        """
        Метод удаляет запись из избранного. Если аккаунт ВК не находится в избранном у других пользователей бота,
        он удаляется вместе с картинками
        :param vk_user_id_: str(50) - VK User ID to be removed
        :param vk_owner_id_: str(50) - Owner's VK ID
        """

        # Checking is record exists, if not - exiting

        with self.session as db:
            user_pk_ = self.get_pk(m.VKUser.id, vk_user_id_)
            if user_pk_ == -1:
                return False
            my_query = db.query(m.Favorite.user_id).filter_by(user_id=user_pk_)
            if my_query.count() == 0:
                return False

            owner_pk_ = self.get_pk(m.Owner.id, vk_owner_id_)
            if owner_pk_ == -1:
                return False
            my_query = db.query(m.Favorite.owner_id).filter_by(owner_id=owner_pk_)
            if my_query.count() == 0:
                return False

            db.query(m.Favorite).filter_by(
                user_id=user_pk_, owner_id=owner_pk_
            ).delete()
            db.commit()

            # checking are there any other owners who added same VK ID into the favorites
            # if no - removing VK ID from other tables
            my_query = db.query(m.Favorite.user_id).filter_by(user_id=user_pk_)
            if my_query.count() == 0:
                db.query(m.Photo).filter_by(user_id=user_pk_).delete()
                db.commit()
                db.query(m.VKUser).filter_by(id=user_pk_).delete()
                db.commit()
                return True

    def create_structure(self):
        """
        Метод создает структуру БД
        :return: None\n
        """

        print("Creating structure")
        m.Base.metadata.create_all(self.engine)

    def delete_structure(self):
        """
        Метод удаляет БД - данные и структуру
        :return: None\n
        """

        print("Deleting structure")
        m.Base.metadata.drop_all(self.engine)

    def add_owner(self, owner_id_: str) -> bool:
        """
        Метод добавляет пользователя в БД
        :param owner_id_: str(50) - owner ID
        :return: boolean - True if record was uploaded, False if not (already exists)
        """
        with self.session as db:
            my_query = db.query(m.Owner.vk_id).filter_by(vk_id=owner_id_)
            if my_query.count() == 0:
                my_record = m.Owner(vk_id=owner_id_)
                db.add(my_record)
                db.commit()
                return True
        return False

    def add_favorite(self, new_record: dict, vk_owner_id_: str) -> bool:
        """
        Метод добавляет запись в избранное, таблицы VKUsers и Photos
        :param new_record: dictionary{
            vk_id:str(50),
            first_name:str(20),
            last_name:str(20),
            city(20):str,
            sex:integer,
            birth_date:date,
            url:str,
            images[{'url':'image_1.jpg', likes: 5}, {'url':'image_2.jpg', likes: 3}, {'url':'image_3.jpg', likes: 15}]
            }
        :param vk_owner_id_: str(50) - Owner's VK ID
        """

        with self.session as db:
            my_query = db.query(m.VKUser.vk_id).filter_by(vk_id=new_record["vk_id"])
            is_user_exists = my_query.count() != 0
            if not is_user_exists:
                # adding IDs into the table VKUsers if not exists
                my_record = m.VKUser(
                    vk_id=new_record["vk_id"],
                    first_name=new_record["first_name"],
                    last_name=new_record["last_name"],
                    city=new_record["city"],
                    sex=new_record["sex"],
                    birth_date=new_record["birth_date"],
                    url=new_record["url"],
                )
                db.add(my_record)
                db.commit()

            # Getting primary keys for the Favorite table
            user_pk_ = self.get_pk(m.VKUser.id, new_record["vk_id"])
            if user_pk_ == -1:
                return False
            owner_pk_ = self.get_pk(m.Owner.id, vk_owner_id_)
            if owner_pk_ == -1:
                return False

            if not is_user_exists:
                # Adding photos into the table Photo if user not exists
                for image in new_record["images"]:
                    my_record = m.Photo(
                        user_id=user_pk_, url=image["url"], likes=image["likes"]
                    )
                    db.add(my_record)
                    db.commit()

            # Adding IDs into the table Favorite if not exists
            my_query = db.query(m.Favorite).filter_by(
                user_id=user_pk_, owner_id=owner_pk_
            )
            if my_query.count() == 0:
                my_record = m.Favorite(user_id=user_pk_, owner_id=owner_pk_)
                db.add(my_record)
                db.commit()
                return True
            return False
