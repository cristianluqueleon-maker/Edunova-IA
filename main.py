import os, secrets
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, String, Integer, Float, Text, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from passlib.context import CryptContext
from pypdf import PdfReader
from docx import Document as WordDoc

APP=os.getenv('APP_NAME','EduNova AI'); Path('data').mkdir(exist_ok=True); Path('uploads').mkdir(exist_ok=True)
engine=create_engine('sqlite:///./data/edunova.db',connect_args={'check_same_thread':False})
DB=sessionmaker(engine,expire_on_commit=False); crypt=CryptContext(schemes=['bcrypt'],deprecated='auto')
app=FastAPI(title=APP); app.add_middleware(SessionMiddleware,secret_key=os.getenv('SESSION_SECRET','local-secret-change'),same_site='lax')
app.mount('/static',StaticFiles(directory='static'),name='static'); tpl=Jinja2Templates(directory='templates')
class Base(DeclarativeBase): pass
class School(Base):
 __tablename__='schools'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(180)); min_grade:Mapped[float]=mapped_column(Float,default=1); max_grade:Mapped[float]=mapped_column(Float,default=5); passing:Mapped[float]=mapped_column(Float,default=3.5); periods:Mapped[int]=mapped_column(Integer,default=4)
class User(Base):
 __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); school_id:Mapped[int]=mapped_column(ForeignKey('schools.id')); email:Mapped[str]=mapped_column(String(180),unique=True); password:Mapped[str]=mapped_column(String(255))
class Student(Base):
 __tablename__='students'; id:Mapped[int]=mapped_column(primary_key=True); school_id:Mapped[int]=mapped_column(ForeignKey('schools.id'),index=True); first:Mapped[str]=mapped_column(String(100)); last:Mapped[str]=mapped_column(String(100)); grade:Mapped[str]=mapped_column(String(30)); group_name:Mapped[str]=mapped_column(String(20))
class Grade(Base):
 __tablename__='grades'; id:Mapped[int]=mapped_column(primary_key=True); school_id:Mapped[int]=mapped_column(ForeignKey('schools.id'),index=True); student_id:Mapped[int]=mapped_column(ForeignKey('students.id')); subject:Mapped[str]=mapped_column(String(100)); period:Mapped[int]=mapped_column(Integer); score:Mapped[float]=mapped_column(Float)
class Document(Base):
 __tablename__='documents'; id:Mapped[int]=mapped_column(primary_key=True); school_id:Mapped[int]=mapped_column(ForeignKey('schools.id'),index=True); filename:Mapped[str]=mapped_column(String(255)); kind:Mapped[str]=mapped_column(String(80)); body:Mapped[str]=mapped_column(Text); analysis:Mapped[str]=mapped_column(Text)
Base.metadata.create_all(engine)
def dbdep():
 d=DB()
 try: yield d
 finally: d.close()
def getuser(req,d):
 return d.get(User,req.session.get('uid')) if req.session.get('uid') else None
def auth(req,d):
 u=getuser(req,d)
 if not u: raise HTTPException(401,'Inicia sesión')
 return u
def render(req,name,**kw): return tpl.TemplateResponse(name,{'request':req,'app':APP,**kw})
@app.on_event('startup')
def init():
 d=DB()
 if not d.scalar(select(School).limit(1)):
  s=School(name='Colegio Nuestra Esperanza');d.add(s);d.flush();d.add(User(school_id=s.id,email=os.getenv('ADMIN_EMAIL','admin@demo.edu.co'),password=crypt.hash(os.getenv('ADMIN_PASSWORD','ChangeMe123!'))))
  for a,b in [('Valentina','Rojas'),('Juan','Pérez Díaz'),('Sofía','Martínez'),('Mateo','González'),('Camila','Torres')]: d.add(Student(school_id=s.id,first=a,last=b,grade='8°',group_name='A'))
  d.commit()
 d.close()
@app.get('/')
def root(req:Request,d:Session=Depends(dbdep)): return RedirectResponse('/dashboard' if getuser(req,d) else '/login',303)
@app.get('/login')
def login(req:Request): return render(req,'login.html',error=None)
@app.post('/login')
def signin(req:Request,email:str=Form(...),password:str=Form(...),d:Session=Depends(dbdep)):
 u=d.scalar(select(User).where(User.email==email.lower().strip()))
 if not u or not crypt.verify(password,u.password): return render(req,'login.html',error='Correo o contraseña incorrectos')
 req.session['uid']=u.id;return RedirectResponse('/dashboard',303)
@app.get('/logout')
def logout(req:Request):req.session.clear();return RedirectResponse('/login',303)
@app.get('/dashboard')
def dashboard(req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);students=d.scalars(select(Student).where(Student.school_id==s.id)).all();grades=d.scalars(select(Grade).where(Grade.school_id==s.id)).all();docs=d.scalars(select(Document).where(Document.school_id==s.id)).all();return render(req,'dashboard.html',user=u,school=s,students=students,grades=grades,docs=docs,nav='dashboard')
@app.get('/students')
def students(req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);rows=d.scalars(select(Student).where(Student.school_id==s.id).order_by(Student.last)).all();return render(req,'students.html',user=u,school=s,students=rows,nav='students')
@app.post('/students')
def addstudent(req:Request,first:str=Form(...),last:str=Form(...),grade:str=Form(...),group_name:str=Form(...),d:Session=Depends(dbdep)):
 u=auth(req,d);d.add(Student(school_id=u.school_id,first=first.strip(),last=last.strip(),grade=grade,group_name=group_name));d.commit();return RedirectResponse('/students',303)
@app.post('/students/{sid}/delete')
def delstudent(sid:int,req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.scalar(select(Student).where(Student.id==sid,Student.school_id==u.school_id))
 if s:d.query(Grade).filter(Grade.student_id==sid,Grade.school_id==u.school_id).delete();d.delete(s);d.commit()
 return RedirectResponse('/students',303)
@app.get('/grades')
def gradepage(req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);students=d.scalars(select(Student).where(Student.school_id==s.id)).all();grades=d.scalars(select(Grade).where(Grade.school_id==s.id).order_by(Grade.id.desc())).all();return render(req,'grades.html',user=u,school=s,students=students,grades=grades,nav='grades')
@app.post('/grades')
def addgrade(req:Request,student_id:int=Form(...),subject:str=Form(...),period:int=Form(...),score:float=Form(...),d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);student=d.scalar(select(Student).where(Student.id==student_id,Student.school_id==s.id))
 if not student or not s.min_grade<=score<=s.max_grade:raise HTTPException(400,'Nota fuera de escala')
 d.add(Grade(school_id=s.id,student_id=student_id,subject=subject,period=period,score=score));d.commit();return RedirectResponse('/grades',303)
@app.get('/settings')
def settings(req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);return render(req,'settings.html',user=u,school=s,nav='settings')
@app.post('/settings')
def savesettings(req:Request,name:str=Form(...),min_grade:float=Form(...),max_grade:float=Form(...),passing:float=Form(...),periods:int=Form(...),d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id)
 if min_grade>=max_grade or not min_grade<=passing<=max_grade or periods not in range(1,7):raise HTTPException(400,'Configuración inválida')
 s.name=name;s.min_grade=min_grade;s.max_grade=max_grade;s.passing=passing;s.periods=periods;d.commit();return RedirectResponse('/settings?saved=1',303)
def extract(path,suffix):
 if suffix=='.pdf':return '\n'.join(p.extract_text() or '' for p in PdfReader(str(path)).pages)
 if suffix=='.docx':return '\n'.join(p.text for p in WordDoc(str(path)).paragraphs)
 if suffix=='.txt':return path.read_text(errors='ignore')
 raise ValueError('Solo PDF, DOCX o TXT')
def ai_summary(txt,name):
 key=os.getenv('OPENAI_API_KEY','')
 if not key:return 'Texto extraído. Para activar la IA, configura OPENAI_API_KEY en .env.'
 from openai import OpenAI
 r=OpenAI(api_key=key).responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),input=[{'role':'system','content':'Analiza documentos escolares colombianos. Resume solo información explícita, no inventes reglas y marca ambigüedades para revisión humana.'},{'role':'user','content':f'Documento: {name}\nContenido:\n{txt[:45000]}'}]);return r.output_text
@app.get('/documents')
def documents(req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);s=d.get(School,u.school_id);docs=d.scalars(select(Document).where(Document.school_id==s.id)).all();return render(req,'documents.html',user=u,school=s,docs=docs,nav='documents')
@app.post('/documents/upload')
async def upload(req:Request,file:UploadFile=File(...),kind:str=Form('Otro'),d:Session=Depends(dbdep)):
 u=auth(req,d);ext=Path(file.filename or '').suffix.lower()
 if ext not in ['.pdf','.docx','.txt']:raise HTTPException(400,'Formato no permitido')
 data=await file.read()
 if len(data)>15*1024*1024:raise HTTPException(413,'Máximo 15 MB')
 path=Path('uploads')/(secrets.token_hex(8)+ext);path.write_bytes(data)
 try:body=extract(path,ext);summary=ai_summary(body,file.filename or path.name)
 except Exception as e:path.unlink(missing_ok=True);raise HTTPException(400,str(e))
 d.add(Document(school_id=u.school_id,filename=file.filename or path.name,kind=kind,body=body[:130000],analysis=summary));d.commit();return RedirectResponse('/documents',303)
@app.get('/documents/{did}')
def docdetail(did:int,req:Request,d:Session=Depends(dbdep)):
 u=auth(req,d);doc=d.scalar(select(Document).where(Document.id==did,Document.school_id==u.school_id))
 if not doc:raise HTTPException(404,'No encontrado')
 return render(req,'docdetail.html',user=u,school=d.get(School,u.school_id),doc=doc,nav='documents')
@app.get('/health')
def health():return {'status':'ok'}
