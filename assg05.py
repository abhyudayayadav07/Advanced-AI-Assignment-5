import random
import subprocess
import time
import os
import psutil
import z3


class SATEncoder:

    def __init__(self):
        self.var_map = {}
        self.var_count = 0
        self.clauses = []

    def new_var(self, name):
        if name not in self.var_map:
            self.var_count += 1
            self.var_map[name] = self.var_count
        return self.var_map[name]

    def add_clause(self, clause):
        self.clauses.append(clause)

    def write_dimacs(self, filename):

        with open(filename, "w") as f:

            f.write(f"p cnf {self.var_count} {len(self.clauses)}\n")

            for c in self.clauses:
                f.write(" ".join(map(str,c)) + " 0\n")



def read_input(file):

    M = 0
    courses = []

    with open(file) as f:

        for line in f:

            if line.startswith("%") or len(line.strip())==0:
                continue

            parts = line.split()

            if parts[0] == "M":
                M = int(parts[1])

            elif parts[0] == "C":

                cid = int(parts[1])
                s = int(parts[2])
                d = int(parts[3])
                t = int(parts[4])

                courses.append((cid,s,d,t))

    return M,courses



def encode_option1(M,courses):

    enc = SATEncoder()

    z = {}

    for cid,s,d,t in courses:

        latest = d - t + 1

        for j in range(1,M+1):
            for day in range(s,latest+1):

                name = f"z_{cid}_{j}_{day}"
                z[(cid,j,day)] = enc.new_var(name)

    
    for cid,s,d,t in courses:

        latest = d - t + 1

        clause=[]

        for j in range(1,M+1):
            for day in range(s,latest+1):

                clause.append(z[(cid,j,day)])

        enc.add_clause(clause)

        vars_list = clause

        for i in range(len(vars_list)):
            for k in range(i+1,len(vars_list)):

                enc.add_clause([-vars_list[i],-vars_list[k]])

    
    for i in range(len(courses)):

        cid1,s1,d1,t1 = courses[i]

        for k in range(i+1,len(courses)):

            cid2,s2,d2,t2 = courses[k]

            latest1 = d1 - t1 + 1
            latest2 = d2 - t2 + 1

            for j in range(1,M+1):

                for t_start in range(s1,latest1+1):
                    for u_start in range(s2,latest2+1):

                        end1 = t_start + t1 - 1
                        end2 = u_start + t2 - 1

                        if not(end1 < u_start or end2 < t_start):

                            enc.add_clause([
                                -z[(cid1,j,t_start)],
                                -z[(cid2,j,u_start)]
                            ])

    return enc



def encode_option2(M,courses):

    enc = SATEncoder()

    x={}
    y={}

    
    for cid,s,d,t in courses:

        for j in range(1,M+1):

            x[(cid,j)] = enc.new_var(f"x_{cid}_{j}")

        latest = d - t + 1

        for day in range(s,latest+1):

            y[(cid,day)] = enc.new_var(f"y_{cid}_{day}")

    
    for cid,s,d,t in courses:

        clause=[x[(cid,j)] for j in range(1,M+1)]
        enc.add_clause(clause)

        for j1 in range(1,M+1):
            for j2 in range(j1+1,M+1):

                enc.add_clause([-x[(cid,j1)],-x[(cid,j2)]])

    
    for cid,s,d,t in courses:

        latest = d - t + 1

        starts=[]

        for day in range(s,latest+1):
            starts.append(y[(cid,day)])

        enc.add_clause(starts)

        for i in range(len(starts)):
            for k in range(i+1,len(starts)):

                enc.add_clause([-starts[i],-starts[k]])

    
    for i in range(len(courses)):

        cid1,s1,d1,t1 = courses[i]

        for k in range(i+1,len(courses)):

            cid2,s2,d2,t2 = courses[k]

            latest1 = d1 - t1 + 1
            latest2 = d2 - t2 + 1

            for t_start in range(s1,latest1+1):
                for u_start in range(s2,latest2+1):

                    end1 = t_start + t1 - 1
                    end2 = u_start + t2 - 1

                    if not(end1 < u_start or end2 < t_start):

                        for room in range(1,M+1):

                            enc.add_clause([
                                -x[(cid1,room)],
                                -x[(cid2,room)],
                                -y[(cid1,t_start)],
                                -y[(cid2,u_start)]
                            ])

    return enc



def clause_stats(encoder):

    c2=0
    c3=0
    c3p=0

    for c in encoder.clauses:

        l=len(c)

        if l==2:
            c2+=1
        elif l==3:
            c3+=1
        elif l>3:
            c3p+=1

    return c2,c3,c3p



def generate_random_test(file):

    M=random.randint(3,8)
    N=random.randint(5,15)

    with open(file,"w") as f:

        f.write(f"M {M}\n")

        for i in range(1,N+1):

            s=random.randint(1,20)
            t=random.randint(1,5)
            d=s+random.randint(t+1,20)

            f.write(f"C {i} {s} {d} {t}\n")



def run_solver(solver,file):

    start=time.time()

    p=subprocess.run([solver,file],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)

    end=time.time()

    runtime=end-start

    mem=psutil.Process().memory_info().rss/1024/1024

    return runtime,mem



def run_experiment():

    solvers=["z3","minisat","glucose"]

    results=[]

    for i in range(1,101):

        test=f"test_{i}.txt"

        generate_random_test(test)

        M,courses=read_input(test)

        enc1=encode_option1(M,courses)
        enc2=encode_option2(M,courses)

        cnf1=f"opt1_{i}.cnf"
        cnf2=f"opt2_{i}.cnf"

        enc1.write_dimacs(cnf1)
        enc2.write_dimacs(cnf2)

        stat1=clause_stats(enc1)
        stat2=clause_stats(enc2)

        for solver in solvers:

            t1,m1=run_solver(solver,cnf1)
            t2,m2=run_solver(solver,cnf2)

            results.append([
                i,solver,
                "opt1",enc1.var_count,len(enc1.clauses),
                *stat1,t1,m1
            ])

            results.append([
                i,solver,
                "opt2",enc2.var_count,len(enc2.clauses),
                *stat2,t2,m2
            ])

    print("Test Solver Encoding Vars Clauses 2-lit 3-lit 3+lit Time Memory")

    for r in results:
        print(*r)



if __name__=="__main__":

    run_experiment()

